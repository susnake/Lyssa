import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
# Конфигурация уровня доступа
lock_config = {
    "access_level": "owner"  # owner, admin, all
}


async def set_access_level(level: str):
    # Устанавливает уровень доступа: owner, admin, all.
    if level not in ["owner", "admin", "all"]:
        logger.error(f"Недопустимый уровень доступа: {level}")
        raise ValueError("Уровень доступа должен быть 'owner', 'admin' или 'all'.")

    global lock_config
    lock_config["access_level"] = level
    logger.info(f"Уровень доступа установлен на: {level}")


def get_access_level() -> str:
    # Возвращает текущий уровень доступа.
    return lock_config.get("access_level", "owner")


async def has_permission(update, context: ContextTypes.DEFAULT_TYPE, required_level: str = None) -> bool:
    # Проверяет, имеет ли пользователь необходимый уровень доступа.
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    current_level = get_access_level()

    if current_level == "all":
        return True

    try:
        user_status = await context.bot.get_chat_member(chat_id, user_id)
        if current_level == "admin" and user_status.status in ["administrator", "creator"]:
            return True
        if current_level == "owner" and user_status.status == "creator":
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке прав пользователя {user_id}: {e}")

    return False


async def lock_command(update, context: ContextTypes.DEFAULT_TYPE):
    # Команда для изменения уровня доступа.
    if not context.args:
        await update.message.reply_text(f"Текущий уровень доступа: {get_access_level()}")
        return

    level = context.args[0].lower()
    try:
        set_access_level(level)
        await update.message.reply_text(f"Уровень доступа изменен на: {level}")
    except ValueError as e:
        await update.message.reply_text(str(e))
