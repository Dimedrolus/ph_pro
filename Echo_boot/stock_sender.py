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