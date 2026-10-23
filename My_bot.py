import requests
import time


import os
from dotenv import load_data  # Загружает данные из файла .env

load_data()
# Теперь токен лежит в безопасности в переменной:
TOKEN = os.getenv("BOT_TOKEN") 



offset = 0

print("Бот запущен и ждёт сообщения... (остановка: Ctrl+C)")

while True:
    # 1. Запрос входящих: сеть может оборваться — ловим и повторяем, offset НЕ трогаем
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()
    except requests.exceptions.RequestException as e:
        print(f"[сеть] getUpdates оборвался ({e.__class__.__name__}), повторяю через 3 сек...")
        time.sleep(3)
        continue

    # 2. Разбор апдейтов
    for upd in r["result"]:
        offset = upd["update_id"] + 1
        if "message" not in upd:
            continue
        chat_id = upd["message"]["chat"]["id"]
        text = upd["message"].get("text", "")
        print(f"Входящее: chat_id={chat_id}, text={text!r}")

        # 3. Отправка ответа: сеть может оборваться — ловим, бот остаётся жив
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"Мне написали вот что: {text}"}
            )
        except requests.exceptions.RequestException as e:
            print(f"[сеть] sendMessage оборвался ({e.__class__.__name__}) — ответ мог потеряться, но бот жив")