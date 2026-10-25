import os
import sys
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ПУТЕЙ (АРХИТЕКТУРА)
# ==========================================

# Текущая директория скрипта (например, C:\ph_pro\Echo_boot\)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Корневая директория проекта (на уровень выше, например, C:\ph_pro\)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Пути к общим ресурсам в корне
ENV_PATH = os.path.join(BASE_DIR, ".env")
DB_PATH = os.path.join(BASE_DIR, "subscribers.txt")

# Локальные пути для этого проекта
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "sender.log")

# Создаем папку logs, если её нет
if not os.path.exists(LOGS_DIR):
    try:
        os.makedirs(LOGS_DIR)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать папку логов {LOGS_DIR}: {e}")
        sys.exit(1)

# ==========================================
# 2. СИСТЕМА ЛОГИРОВАНИЯ С РОТАЦИЕЙ
# ==========================================

def log(message, level="INFO"):
    """Пишет сообщение в консоль и в файл с ротацией по размеру."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] [{level}] {message}"
    
    # Вывод в консоль (для отладки вручную)
    print(formatted_msg)
    
    # Проверка размера файла перед записью (ротация > 1 МБ)
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
            archive_name = LOG_FILE.replace(".log", f"_old_{int(time.time())}.log")
            os.rename(LOG_FILE, archive_name)
            log("Старый лог переименован в архив.", "WARN")
            
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        # Если не смогли написать в файл, пишем только в консоль, но не крашим процесс
        print(f"Ошибка записи в лог-файл: {e}")

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

log("--- ЗАПУСК SENDER.PY ---")
log(f"Рабочая директория: {SCRIPT_DIR}")
log(f"Корневая директория: {BASE_DIR}")

# ==========================================
# 4. ЛОГИКА РАССЫЛКИ
# ==========================================

def send_message_to_all(text):
    """Читает общую базу подписчиков и рассылает сообщения."""
    
    if not os.path.exists(DB_PATH):
        log(f"База данных {DB_PATH} не найдена! Рассылка отменена.", "ERROR")
        return

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            chat_ids = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        log(f"Ошибка чтения базы данных: {e}", "ERROR")
        return
    
    if not chat_ids:
        log("Список подписчиков пуст.", "WARN")
        return

    total_users = len(chat_ids)
    log(f"Начинаю рассылку для {total_users} пользователей...", "INFO")

    success_count = 0
    fail_count = 0
    
    # Inline-кнопка возврата в меню
    reply_markup_json = json.dumps({
        "inline_keyboard": [[{"text": "👋 Вернуться в меню", "callback_data": "back_to_menu"}]]
    })

    for cid_str in chat_ids:
        try:
            cid = int(cid_str)
            
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": cid, 
                    "text": text,
                    "reply_markup": reply_markup_json
                },
                timeout=10  
            )
            
            if resp.status_code == 200:
                success_count += 1
                # Логируем успех кратко, чтобы не забивать лог при большой базе
                if total_users <= 10: 
                    log(f"[OK] Доставлено {cid}", "DEBUG")
            else:
                fail_count += 1
                err_msg = resp.text[:100] # Обрезаем длинные ответы сервера
                log(f"[FAIL] Ошибка API для {cid}: {err_msg}", "ERROR")
                
        except ValueError:
            fail_count += 1
            log(f"[ERROR] Некорректный ID в базе: '{cid_str}'", "ERROR")
        except requests.exceptions.RequestException as e:
            fail_count += 1
            log(f"[NETWORK] Сетевая ошибка для {cid}: {e.__class__.__name__}", "WARN")
            
        # Пауза между отправками (Rate Limit protection)
        time.sleep(0.5) 

    log(f"Рассылка завершена. Успех: {success_count}, Ошибок: {fail_count}", "INFO")

# ==========================================
# 5. ТОЧКА ВХОДА
# ==========================================

if __name__ == "__main__":
    # Текст сообщения. Можно менять или читать из аргументов командной строки позже.
    message_text = (
        "⏰ **АВТОМАТИЧЕСКОЕ УВЕДОМЛЕНИЕ**\n\n"
        "Привет! Это тест работы твоего будильника.\n"
        "Архитектура: Конфиги в корне, логи локально.\n"
        "Если ты видишь это — планировщик Windows работает правильно."
    )
    
    send_message_to_all(message_text)
    log("--- КОНЕЦ РАБОТЫ SENDER.PY ---")