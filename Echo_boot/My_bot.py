import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
# Загружаем переменные из файла .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: BOT_TOKEN не найден в файле .env. Проверь наличие файла и строки BOT_TOKEN=...")

FILE_NAME = "subscribers.txt"
offset = 0

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ---
def save_chat_id(chat_id):
    """Проверяет наличие ID в файле и добавляет, если его нет."""
    try:
        # Читаем существующие ID
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            ids = [line.strip() for line in f.readlines()]
        
        if str(chat_id) not in ids:
            # Если ID новый — дописываем
            with open(FILE_NAME, "a", encoding="utf-8") as f:
                f.write(f"{chat_id}\n")
            return True  # Новый подписчик
        else:
            return False # Уже есть в базе
    except FileNotFoundError:
        # Если файла ещё нет, создаём его и пишем первый ID
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(f"{chat_id}\n")
        return True

print("Бот запущен. Жду команд... (/start, /help, /time)")
print(f"Токен загружен успешно (длина {len(TOKEN)} символов).")

while True:
    # 1. Опрос сервера Telegram (Long Polling)
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()
    except requests.exceptions.RequestException as e:
        print(f"[сеть] getUpdates оборвался ({e.__class__.__name__}), повторяю через 3 сек...")
        time.sleep(3)
        continue

    # 2. Обработка полученных сообщений
    for upd in r["result"]:
        offset = upd["update_id"] + 1
        
        msg = upd.get("message", {})
        if "text" not in msg:
            continue
            
        chat_id = msg["chat"]["id"]
        raw_text = msg["text"].strip()
        text_lower = raw_text.lower() # Для проверки команд без учета регистра
        
        response_text = ""
        
        # --- ЛОГИКА КОМАНД ---
        if text_lower == "/start":
            is_new = save_chat_id(chat_id)
            if is_new:
                response_text = "👋 Привет! Я записал тебя в базу.\nТеперь могу присылать уведомления."
            else:
                response_text = "✅ Ты уже в базе. Всё работает."
                
        elif text_lower == "/help":
            response_text = (
                "Я умею:\n"
                "/start - зарегистрироваться\n"
                "/help - эта справка\n"
                "/time - показать текущее время сервера\n\n"
                "Любой другой текст я просто повторю."
            )
            
        elif text_lower == "/time":
            now = datetime.now().strftime("%H:%M:%S")
            response_text = f"⏰ Сейчас на сервере: {now}"
            
        else:
            # Эхо для всего остального
            response_text = f"Эхо приняло: {raw_text}"

     # 3. Отправка ответа пользователю (с попытками)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": response_text},
                    timeout=10  # Ждем максимум 10 секунд, не бесконечно
                )
                if resp.status_code == 200:
                    break  # Успешно отправили, выходим из цикла повторов
                else:
                    print(f"[сеть] Ответ не доставлен (код {resp.status_code}), пробую еще...")
                    
            except requests.exceptions.RequestException as e:
                print(f"[сеть] Попытка {attempt + 1}/{max_retries} сорвалась ({e.__class__.__name__})")
                if attempt < max_retries - 1:
                    time.sleep(2) # Пауза перед повтором
                else:
                    print("[!] Сообщение потеряно окончательно.")