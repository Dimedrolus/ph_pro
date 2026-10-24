import logging
import os
import csv
import random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Этапы диалога (состояния для ConversationHandler)
PHONE, CHILD_NAME, CHILD_AGE = range(3)

# ID вашего Telegram-аккаунта (замените на свой числовой ID, чтобы только вы могли проводить розыгрыш!)
# Узнать свой ID можно у бота @userinfobot
ADMIN_ID = 5179402436  

CSV_FILE = "participants.csv"

# Создаем CSV файл с заголовками, если его еще нет
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Telegram ID', 'Username', 'Телефон', 'Имя ребенка', 'Возраст ребенка'])

# --- НАЧАЛО ДИАЛОГА И СБОР ДАННЫХ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Старт розыгрыша, запрашиваем телефон кнопкой"""
    user_id = update.effective_user.id
    
    # Проверяем, не участвует ли уже этот пользователь
    if is_user_registered(user_id):
        await update.message.reply_text("Вы уже зарегистрированы в розыгрыше пиццы! Ожидайте результатов. 🍕")
        return ConversationHandler.END

    # Создаем кнопку для отправки телефона
    contact_keyboard = KeyboardButton(text="📱 Поделиться телефоном", request_contact=True)
    custom_keyboard = [[contact_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Участвуй в розыгрыше вкусной пиццы! 🍕\n\n"
        "Для участия, пожалуйста, нажмите кнопку ниже и поделитесь своим номером телефона:",
        reply_markup=reply_markup
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем телефон и спрашиваем имя ребенка"""
    contact = update.message.contact
    # Сохраняем телефон в контекст пользователя, чтобы не потерять
    context.user_data['phone'] = contact.phone_number

    await update.message.reply_text(
        "Спасибо! Теперь напишите, пожалуйста, как зовут вашего ребенка:",
        reply_markup=ReplyKeyboardRemove() # Убираем кнопку телефона
    )
    return CHILD_NAME

async def get_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем имя ребенка и спрашиваем возраст"""
    context.user_data['child_name'] = update.message.text

    await update.message.reply_text("И последний вопрос: сколько лет вашему ребенку?")
    return CHILD_AGE

async def get_child_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем возраст, сохраняем всё в CSV и завершаем опрос"""
    context.user_data['child_age'] = update.message.text
    
    user = update.effective_user
    
    # Сохраняем данные в файл CSV
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            user.id,
            f"@{user.username}" if user.username else "Нет",
            context.user_data['phone'],
            context.user_data['child_name'],
            context.user_data['child_age']
        ])

    await update.message.reply_text(
        "Поздравляем! 🎉 Вы успешно зарегистрированы в розыгрыше пиццы.\n"
        "Когда розыгрыш завершится, бот пришлет вам уведомление в случае победы! 🍕"
    )
    # Очищаем временные данные пользователя
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Прерывание заполнения данных"""
    await update.message.reply_text("Регистрация прервана.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def is_user_registered(user_id: int) -> bool:
    """Проверка, есть ли уже такой ID в базе"""
    if not os.path.exists(CSV_FILE):
        return False
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None) # Пропускаем заголовок
        for row in reader:
            if row and row[0] == str(user_id):
                return True
    return False

# --- ФУНКЦИИ АДМИНИСТРАТОРА (ОПРЕДЕЛЕНИЕ ПОБЕДИТЕЛЯ) ---

async def draw_pizza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /draw для выбора случайного победителя (только для админа)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для проведения розыгрыша!")
        return

    participants = []
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row:
                participants.append(row)

    if not participants:
        await update.message.reply_text("В розыгрыше пока никто не участвует. База пуста!")
        return

    # Выбираем случайную строку из списка участников
    winner = random.choice(participants)
    winner_id = int(winner[0])
    winner_username = winner[1]
    winner_phone = winner[2]
    winner_child = winner[3]

    # 1. Пишем админу, кто победил, со всеми картами
    await update.message.reply_text(
        f"🎉 Розыгрыш проведен!\n\n"
        f"👑 ПОБЕДИТЕЛЬ:\n"
        f"Telegram ID: {winner_id}\n"
        f"Ник: {winner_username}\n"
        f"Телефон: {winner_phone}\n"
        f"Ребенок: {winner_child}"
    )

    # 2. Автоматически отправляем сообщение самому победителю в ЛС!
    try:
        await context.bot.send_message(
            chat_id=winner_id,
            text="🎉 Поздравляем!!! Вы выиграли горячую пиццу! 🍕🎁\n\n"
                 "Приходите и заберите свой приз. Назовите на кассе ваш номер телефона, который вы указывали боту."
        )
        await update.message.reply_text("🔔 Победитель успешно уведомлен ботом в личные сообщения!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Не удалось автоматически уведомить победителя в ЛС (возможно, он заблокировал бота): {e}")


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token: return

    application = Application.builder().token(token).build()

    # Настраиваем пошаговый опрос (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            CHILD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_child_name)],
            CHILD_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_child_age)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    # Регистрируем секретную команду для админа
    application.add_handler(CommandHandler("draw", draw_pizza))

    logger.info("Бот для розыгрыша пиццы успешно запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
