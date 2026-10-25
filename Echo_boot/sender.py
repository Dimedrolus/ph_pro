import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

# --- ЛОГИРОВАНИЕ В ФАЙЛ ---
LOG_FILE = "sender_log.txt"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg) # Для терминала
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n") # Для файла

# --- НАСТРОЙКИ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
FILE_NAME = "subscribers.txt"

log("--- ЗАПУСК SENDER.PY ---")

if not TOKEN:
    log("КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден в .env!")
    exit(1)

def send_message_to_all(text):
    if not os.path.exists(FILE_NAME):
        log(f"[!] Файл {FILE_NAME} не найден. Путь поиска: {os.getcwd()}")
        return

    with open(FILE_NAME, "r", encoding="utf-8") as f:
        chat_ids = [line.strip() for line in f.readlines()]
    
    if not chat_ids:
        log("[*] Список подписчиков пуст.")
        return

    log(f"[*] Начинаю рассылку для {len(chat_ids)} пользователей...")

    success_count = 0
    fail_count = 0
    
    for cid_str in chat_ids:
        try:
            cid = int(cid_str)
            
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": cid,
                    "text": text,
                    "reply_markup": json.dumps({
                        "inline_keyboard": [[{"text": "👋 Вернуться в меню", "callback_data": "back_to_menu"}]]
                    })
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                success_count += 1
                log(f"[OK] Доставлено пользователю {cid}")
            else:
                fail_count += 1
                log(f"[FAIL] Ошибка API для {cid}: {resp.text[:100]}") # Пишем первые 100 символов ошибки
                
        except Exception as e:
            fail_count += 1
            log(f"[ERROR] Исключение при отправке {cid_str}: {e}")
            
        import time
        time.sleep(0.5) 

    log(f"[*] Рассылка завершена. Успех: {success_count}, Ошибок: {fail_count}")

if __name__ == "__main__":
    test_text = "⏰ ДОБРЫЙ ДЕНЬ!\nЭто автоматическое уведомление от твоего бота.\nНадеюсь, у тебя всё отлично!"
    send_message_to_all(test_text)
    log("--- КОНЕЦ РАБОТЫ SENDER.PY ---")