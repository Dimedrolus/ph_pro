import os
import requests
import time
import json # Нужен для формирования JSON структуры клавиатуры
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: BOT_TOKEN не найден в файле .env.")

FILE_NAME = "subscribers.txt"
offset = 0

# --- СОЗДАНИЕ КЛАВИАТУРЫ ---
def get_main_menu():
    """Формирует структуру reply_markup для главного меню"""
    keyboard_data = {
        "keyboard": [
            [{"text": "🕒 Показать время"}, {"text": "❓ Справка"}],
            [{"text": "🔄 Перезапуск / Start"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    return json.dumps(keyboard_data)

MAIN_MENU_JSON = get_main_menu()

def save_chat_id(chat_id):
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            ids = [line.strip() for line in f.readlines()]
        
        if str(chat_id) not in ids:
            with open(FILE_NAME, "a", encoding="utf-8") as f:
                f.write(f"{chat_id}\n")
            return True
        else:
            return False
    except FileNotFoundError:
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(f"{chat_id}\n")
        return True

print("Бот запущен. Жду команд... (/start, /help, /time)")
print(f"Токен загружен успешно (длина {len(TOKEN)} символов).")

while True:
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()
    except requests.exceptions.RequestException as e:
        print(f"[сеть] getUpdates оборвался ({e.__class__.__name__}), повторяю через 3 сек...")
        time.sleep(3)
        continue

    for upd in r["result"]:
        offset = upd["update_id"] + 1
        
        msg = upd.get("message", {})
        if "text" not in msg:
            continue
            
        chat_id = msg["chat"]["id"]
        raw_text = msg["text"].strip()
        text_lower = raw_text.lower() 
        
        response_text = ""
        
        # --- ЛОГИКА ОТВЕТА НА ТЕКСТ КОМАНДЫ ИЛИ НАЖАТИЕ КНОПКИ ---
        # Когда пользователь жмет кнопку, Telegram отправляет текст этой кнопки как обычное сообщение!
        # Поэтому наша проверка startswith('/') все еще работает, если мы хотим поддерживать и ручной ввод.
        # Но лучше проверять точное совпадение текста кнопки.
        
        if text_lower == "/start" or raw_text == "🔄 Перезапуск / Start":
            is_new = save_chat_id(chat_id)
            if is_new:
                response_text = "👋 Привет! Я записал тебя в базу.\nНажимай кнопки ниже:"
            else:
                response_text = "✅ Ты уже в базе. Всё работает."
                
        elif text_lower == "/help" or raw_text == "❓ Справка":
            response_text = (
                "Я умею:\n"
                "• Показывать время\n"
                "• Давать справку\n"
                "\nВыбери действие кнопкой 👇"
            )
            
        elif text_lower == "/time" or raw_text == "🕒 Показать время":
            now = datetime.now().strftime("%H:%M:%S")
            response_text = f"⏰ Сейчас на сервере: {now}"
            
        else:
            # Эхо для всего остального
            response_text = f"Эхо приняло: {raw_text}"

        # 3. Отправка ответа пользователю (с клавиатурой!)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id, 
                        "text": response_text,
                        "reply_markup": MAIN_MENU_JSON  # <-- ВОТ ГДЕ МАГИЯ
                    },
                    timeout=10  
                )
                if resp.status_code == 200:
                    break  
                else:
                    print(f"[сеть] Ответ не доставлен (код {resp.status_code}), пробую еще...")
                    
            except requests.exceptions.RequestException as e:
                print(f"[сеть] Попытка {attempt + 1}/{max_retries} сорвалась ({e.__class__.__name__})")
                if attempt < max_retries - 1:
                    time.sleep(2) 
                else:
                    print("[!] Сообщение потеряно окончательно.")