import os
import sys
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 1. АРХИТЕКТУРА ПУТЕЙ (как в sender.py)
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
# 4. ЛОГИКА ПОЛУЧЕНИЯ ДАННЫХ С MOEX
# ==========================================

def get_gazp_data():
    """
    Получает последние 5 дневных свечей по акции GAZP с Мосбиржи.
    Возвращает словарь с данными или None при ошибке.
    """
    url = ("https://iss.moex.com/iss/engines/stock/markets/shares/"
           "boards/TQBR/securities/GAZP/candles.json?interval=24&limit=5")
    
    try:
        log("Запрос данных с MOEX...", "DEBUG")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Проверяем структуру ответа
        candles_raw = data.get('candles', {}).get('data', [])
        
        if not candles_raw:
            log("MOEX вернул пустой список свечей.", "WARN")
            return None
            
        # Берем самую свежую свечу (обычно первая в списке для interval=24, но проверим индексацию)
        # В API MOEX данные идут в порядке [open, close, high, low, volume...]
        # Индекс 1 - это Close
        
        # Просто возьмем первую попавшуюся свежую цену для теста
        latest_candle = candles_raw[0] 
        current_price = float(latest_candle[1]) # Close price
        
        # Для примера возьмем вторую как предыдущую, если есть
        prev_price = float(candles_raw[1][1]) if len(candles_raw) > 1 else current_price
        
        change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
        
        return {
            'current': current_price,
            'change_pct': change_pct
        }

    except Exception as e:
        log(f"Ошибка при получении данных MOEX: {e}", "ERROR")
        return None

def format_message(stock_data):
    """Формирует КРАТКИЙ текст сообщения."""
    if not stock_data:
        return "❌ Не удалось получить данные о Газпроме."
    
    price = stock_data['current']
    pct = stock_data['change_pct']
    
    trend_icon = "📈" if pct >= 0 else "📉"
    sign = "+" if pct >= 0 else ""
    
    # Максимально короткий текст
    message = (
        f"{trend_icon} ГАЗПРОМ (GAZP)\n\n"
        f"💰 Цена: {price:.2f} ₽\n"
        f"🔄 Изм.: {sign}{pct:.2f}%\n\n"
        f"(Тестовое сообщение)"
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

    log(f"Отправка отчета по акциям для {len(chat_ids)} пользователей...", "INFO")
    
    success_count = 0
    fail_count = 0
    
    # ВАЖНО: Убираем reply_markup для теста
    payload = {
        "chat_id": None, 
        "text": text
    }

    for cid_str in chat_ids:
        try:
            cid = int(cid_str)
            payload["chat_id"] = cid
            
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json=payload,
                timeout=10  
            )
            
            if resp.status_code == 200:
                success_count += 1
                log(f"[OK] Доставлено {cid}", "DEBUG")
            else:
                fail_count += 1
                # Выводим ПОЛНУЮ ошибку, чтобы понять причину
                error_msg = resp.text
                log(f"[FAIL] Ошибка API для {cid}: {error_msg}", "ERROR") 
                
        except ValueError:
            fail_count += 1
            log(f"Некорректный ID: '{cid_str}'", "ERROR")
        except requests.exceptions.RequestException as e:
            fail_count += 1
            log(f"Сетевая ошибка для {cid}: {e.__class__.__name__}", "WARN")
            
        time.sleep(0.5) 

    log(f"Готово. Успех: {success_count}, Ошибок: {fail_count}", "INFO")
# ==========================================
# 6. ТОЧКА ВХОДА
# ==========================================

if __name__ == "__main__":
    send_stock_report()
    log("--- КОНЕЦ РАБОТЫ STOCK_SENDER.PY ---")