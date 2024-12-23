# modules/banUser.py

import logging
import datetime
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config import save_config, load_config  # Импортируем из config.py
from lock import has_permission

logger = logging.getLogger(__name__)

# Значение по умолчанию для 'banUsers'
DEFAULT_BAN_USERS = False  # False: кикать, True: банить

async def set_ban_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /banUsers.
    Использование: /banUsers true|false
    """
    # Проверяем права доступа
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return

    # Проверяем наличие аргументов
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите аргумент: true для бана или false для кика.\n"
            "Пример: /banUsers true"
        )
        return

    # Получаем аргумент и проверяем его корректность
    arg = context.args[0].lower()
    if arg not in ['true', 'false']:
        await update.message.reply_text("Неверный аргумент. Используйте true для бана или false для кика.")
        return

    # Определяем режим на основе аргумента
    mode = arg == 'true'

    try:
        # Загружаем текущую конфигурацию
        config = load_config()

        # Устанавливаем режим
        config['banUsers'] = mode

        # Сохраняем обновлённую конфигурацию
        save_config(config)

        # Определяем строковое представление режима
        mode_str = 'банить' if mode else 'кикать'

        # Отправляем сообщение пользователю
        await update.message.reply_text(f"Режим изменен: {mode_str}.")

        # Логируем изменение
        logger.info(f"Режим изменен на {mode_str} через команду /banUsers.")
    except Exception as e:
        logger.error(f"Ошибка при установке режима бана: {e}")
        await update.message.reply_text("Произошла ошибка при изменении режима. Пожалуйста, попробуйте позже.")

async def ban_or_kick_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """
    Банит или кикает пользователя в зависимости от текущего режима, установленного в конфигурации.
    """
    try:
        # Загружаем текущую конфигурацию
        config = load_config()

        # Получаем текущий режим
        ban_mode = config.get('banUsers', DEFAULT_BAN_USERS)

        if ban_mode:
            # Баним пользователя
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"Пользователь {user_id} забанен в чате {chat_id}.")
        else:
            # Кикаем пользователя без бана
            # Временный бан на 5 секунд, затем отменяем бан
            until_date = int(datetime.datetime.utcnow().timestamp()) + 5
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id, until_date=until_date)
            logger.info(f"Пользователь {user_id} временно забанен для кика из чата {chat_id}.")
            # Ждём 5 секунд, чтобы Telegram обработал бан
            await asyncio.sleep(5)
            # Снимаем временный бан, что эквивалентно кику
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"Временный бан снят, пользователь {user_id} кикнут из чата {chat_id}.")

    except Exception as e:
        # Получаем текущий режим для логирования
        config = load_config()
        ban_mode = config.get('banUsers', DEFAULT_BAN_USERS)
        action = 'забанить' if ban_mode else 'кикнуть'
        logger.error(f"Ошибка при попытке {action} пользователя {user_id} в чате {chat_id}: {e}")