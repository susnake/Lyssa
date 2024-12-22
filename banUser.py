import logging
from telegram.ext import ContextTypes
from lock import set_access_level, get_access_level, has_permission, lock_command

logger = logging.getLogger(__name__)

# Переменная для управления режимом
ban_mode = False  # False: кикать, True: добавлять в ЧС


async def set_ban_mode(mode: bool):
    # Устанавливает режим обработки: бан или кик.
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return
    global ban_mode
    ban_mode = mode
    logger.info(f"Режим изменен: {'банить' if ban_mode else 'кикать'}")


async def ban_or_kick_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    # Банит или кикает пользователя в зависимости от текущего режима.

    try:
        if ban_mode:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"Пользователь {user_id} добавлен в черный список.")
        else:
            await context.bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"Пользователь {user_id} кикнут из чата.")
    except Exception as e:
        logger.error(f"Ошибка при попытке {'забанить' if ban_mode else 'кикнуть'} пользователя {user_id}: {e}")
