import os
import sys
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 1. АРХИТЕКТУРА ПУТЕЙ
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

ENV_PATH = os.path.join(BASE_DIR, ".env")
DB_PATH = os.path.join(BASE_DIR, "subscribers.txt")
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "stock_sender.log")

if not os.path.exists(LOGS_DIR):
    try:
        os.makedirs(LOGS_DIR)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать папку логов {LOGS_DIR}: {e}")
        sys.exit(1)

# ==========================================
# 2. ЛОГИРОВАНИЕ
# ==========================================
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{level}] {message}"
    print(formatted_msg)
    
    try:
        # Ротация логов: если файл больше 1 МБ, архивируем старый
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
            archive_name = LOG_FILE.replace(".log", f"_old_{int(time.time())}.log")
            os.rename(LOG_FILE, archive_name)
            
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

# ==========================================
# 3. ЗАГРУЗКА КОНФИГУРАЦИИ
# ==========================================
if not os.path.exists(ENV_PATH):
    log(f"Файл .env не найден по пути: {ENV_PATH}", "CRITICAL")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH)
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    log("Переменная BOT_TOKEN отсутствует в .env!", "CRITICAL")
    sys.exit(1)

log("--- ЗАПУСК STOCK_SENDER.PY ---")

# ==========================================
# 4. ПОЛУЧЕНИЕ ДАННЫХ С MOEX
# ==========================================

def get_gazp_data():
    """
    Получает данные GAZP за последние торговые дни.
    Используем selectcolumns для явного указания полей, чтобы не зависеть от порядка колонок API.
    Структура ответа с selectcolumns=DATE,CLOSE,VOLUME:
    Index 0: DATE ('2026-10-24')
    Index 1: CLOSE (114.75) <-- ЦЕНА ЗАКРЫТИЯ
    Index 2: VOLUME (...)
    """
    
    # Формируем URL с явным указанием дат и колонок
    # from=2026-10-01 гарантирует свежие данные (сегодня 25 октября 2026)
    url = ("https://iss.moex.com/iss/engines/stock/markets/shares/"
           "boards/TQBR/securities/GAZP/candles.json?"
           "interval=24&limit=5&from=2026-10-01&to=2026-10-25"
           "&selectcolumns=DATE,CLOSE,VOLUME")
    
    try:
        log("Запрос данных с MOEX...", "DEBUG")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        candles_raw = data.get('candles', {}).get('data', [])
        
        if not candles_raw:
            log("MOEX вернул пустой список.", "WARN")
            return None
        
        # Логируем первую и последнюю свечу целиком для диагностики
        log(f"Сырая первая свеча: {candles_raw[0]}", "DEBUG")
        log(f"Сырая последняя свеча: {candles_raw[-1]}", "DEBUG")
        
        # Берем ПОСЛЕДНЮЮ свечу (самая свежая дата)
        latest_candle = candles_raw[-1]
        
        # Извлекаем Close (индекс 1 благодаря selectcolumns)
        try:
            current_price = float(latest_candle[1]) 
            current_date = str(latest_candle[0])    
        except (IndexError, ValueError, TypeError):
            log("Не удалось извлечь цену Close (индекс 1). Проверьте структуру API.", "ERROR")
            return None

        # Предыдущая свеча для сравнения
        prev_candle = candles_raw[-2] if len(candles_raw) > 1 else latest_candle
        try:
            prev_price = float(prev_candle[1]) 
        except:
            prev_price = current_price 

        change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
        
        return {
            'current': current_price,
            'prev': prev_price,
            'change_pct': change_pct,
            'date': current_date 
        }

    except Exception as e:
        log(f"Ошибка при получении данных MOEX: {e}", "ERROR")
        return None

def format_message(stock_data):
    """Формирует простой текстовый отчет."""
    if not stock_data:
        return "❌ Не удалось получить данные о Газпроме."
    
    price = stock_data['current']
    pct = stock_data['change_pct']
    date_str = stock_data.get('date', 'нет даты')
    
    trend_icon = "📈" if pct >= 0 else "📉"
    sign = "+" if pct >= 0 else ""
    
    message = (
        f"{trend_icon} ГАЗПРОМ (GAZP)\n\n"
        f"💰 Цена закрытия ({date_str}): {price:.2f} ₽\n"
        f"🔄 Изменение: {sign}{pct:.2f}%\n\n"
        f"(Источник: Мосбиржа)"
    )
    return message

# ==========================================
# 5. РАССЫЛКА
# ==========================================

def send_stock_report():
    stock_data = get_gazp_data()
    text = format_message(stock_data)
    
    if not os.path.exists(DB_PATH):
        log("База подписчиков не найдена.", "ERROR")
        return

    with open(DB_PATH, "r", encoding="utf-8") as f:
        chat_ids = [line.strip() for line in f.readlines() if line.strip()]
    
    if not chat_ids:
        log("Нет подписчиков.", "WARN")
        return

    log(f"Отправка отчета для {len(chat_ids)} пользователей...", "INFO")
    
    success_count = 0
    fail_count = 0
    
    for cid_str in chat_ids:
        try:
            cid = int(cid_str)
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": cid, 
                    "text": text
                },
                timeout=10  
            )
            
            if resp.status_code == 200:
                success_count += 1
                log(f"[OK] Доставлено {cid}", "DEBUG")
            else:
                fail_count += 1
                log(f"[FAIL] Ошибка API: {resp.text}", "ERROR") 
                
        except ValueError:
            fail_count += 1
            log(f"Некорректный ID: '{cid_str}'", "ERROR")
        except requests.exceptions.RequestException as e:
            fail_count += 1
            log(f"Сетевая ошибка: {e.__class__.__name__}", "WARN")
            
        time.sleep(0.5) 

    log(f"Готово. Успех: {success_count}, Ошибок: {fail_count}", "INFO")

# ==========================================
# 6. ТОЧКА ВХОДА
# ==========================================

if __name__ == "__main__":
    send_stock_report()
    log("--- КОНЕЦ РАБОТЫ STOCK_SENDER.PY ---")