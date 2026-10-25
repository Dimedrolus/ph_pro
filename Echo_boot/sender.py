import os
import requests
import json
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
FILE_NAME = "subscribers.txt"

if not TOKEN:
    raise ValueError("Ошибка: BOT_TOKEN не найден в .env")

def send_message_to_all(text):
    """Читает subscribers.txt и шлет всем текст"""
    
    # 1. Проверяем наличие файла
    if not os.path.exists(FILE_NAME):
        print("[!] Файл subscribers.txt не найден. Никому не рассылаем.")
        return

    # 2. Читаем ID
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        chat_ids = [line.strip() for line in f.readlines()]
    
    if not chat_ids:
        print("[*] Список подписчиков пуст.")
        return

    print(f"[*] Начинаю рассылку для {len(chat_ids)} пользователей...")

    # 3. Отправляем каждому
    success_count = 0
    fail_count = 0
    
    for cid_str in chat_ids:
        try:
            cid = int(cid_str) # Превращаем строку в число
            
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": cid,
                    "text": text,
                    # Можно добавить inline-кнопку "Продолжить общение", чтобы вернуть юзера в чат
                    "reply_markup": json.dumps({
                        "inline_keyboard": [[{"text": "👋 Вернуться в меню", "callback_data": "back_to_menu"}]]
                    })
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                success_count += 1
                print(f"[OK] Доставлено пользователю {cid}")
            else:
                fail_count += 1
                print(f"[FAIL] Ошибка API для {cid}: {resp.text}")
                
        except Exception as e:
            fail_count += 1
            print(f"[ERROR] Исключение при отправке {cid_str}: {e}")
            
        # Небольшая пауза, чтобы не получить бан от Telegram за флуд (Rate Limit)
        import time
        time.sleep(0.5) 

    print(f"[*] Рассылка завершена. Успех: {success_count}, Ошибок: {fail_count}")

if __name__ == "__main__":
    # Здесь можно задать текст для теста
    test_text = "⏰ ДОБРЫЙ ДЕНЬ!\nЭто автоматическое уведомление от твоего бота.\nНадеюсь, у тебя всё отлично!"
    send_message_to_all(test_text)