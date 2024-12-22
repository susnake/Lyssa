import logging
from telegram import Update
from telegram.ext import ContextTypes
from captcha import save_config, load_config  # Используем функции из captcha.py для работы с конфигурацией

logger = logging.getLogger(__name__)

    #Изменяет время на прохождение капчи.
async def time_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return
    # Загружаем текущую конфигурацию
    global bot_config
    bot_config = load_config()

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите новое время для прохождения капчи в секундах.")
        return

    try:
        new_time_limit = int(context.args[0])
        if new_time_limit <= 0:
            await update.message.reply_text("Время должно быть положительным числом.")
            return

        # Загружаем текущую конфигурацию
        config = load_config()
        config["time_limit"] = new_time_limit
        save_config(config)  # Сохраняем изменения в конфигурации

        await update.message.reply_text(f"Время на прохождение капчи успешно изменено на {new_time_limit} секунд.")
        logger.info(f"Время на прохождение капчи изменено на {new_time_limit} секунд.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите целое число.")
        logger.warning("Некорректное значение времени на прохождение капчи.")