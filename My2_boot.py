import logging
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext
import os
from dotenv import load_dotenv  # Загружает данные из файла .env
import asyncio

# Загружает данные из файла .env
async def load_env():
    await load_dotenv()

load_dotenv()
# Теперь токен лежит в безопасности в переменной:
TOKEN = os.getenv("BOT_TOKEN") 

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def echo(update: Update, context: CallbackContext) -> None:
    """Функция для обработки всех сообщений"""
    update.message.reply_text(update.message.text)

def start(update: Update, context: CallbackContext) -> None:
    """Функция для обработки команды /start"""
    update.message.reply_text('Привет! Я бот, который эхает все, что вам говорят.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Функция для обработки команды /help"""
    update.message.reply_text('Используйте команду /start для начала.')

def error(update: Update, context: CallbackContext) -> None:
    """Функция для обработки ошибок"""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

async def main() -> None:
    """Запуск бота"""
    await load_env()

    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # Регистрация обработчиков
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # Регистрация обработчика ошибок
    dispatcher.add_error_handler(error)

    # Запуск бота
    await updater.start_polling()

    # Запуск обработки обновлений
    await updater.idle()

if __name__ == '__main__':
    asyncio.run(main())
