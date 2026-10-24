import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    await update.message.reply_text('Привет! Я бот, который повторяет все ваши сообщения.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    await update.message.reply_text('Используйте команду /start для начала.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Эхо-эффект: повторение всех текстовых сообщений"""
    await update.message.reply_text(update.message.text)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование ошибок"""
    logger.warning('Обновление "%s" вызвало ошибку "%s"', update, context.error)

def main() -> None:
    """Запуск бота"""
    # Загружаем токен из файла .env
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    
    if not token:
        logger.error("Ошибка: Токен BOT_TOKEN не найден в файле .env!")
        return

    # Создаем приложение (современный синтаксис v20+)
    application = Application.builder().token(token).build()

    # Регистрация обработчиков команд и текста
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Регистрация обработчика ошибок
    application.add_error_handler(error)

    # Запуск бесконечного цикла опроса серверов Telegram
    logger.info("Бот успешно запущен и слушает серверы...")
    application.run_polling()

if __name__ == '__main__':
    main()
