import logging
import json
import os
from telegram import Update
from telegram.ext import ContextTypes

# Инициализация логгера
logger = logging.getLogger(__name__)

# Путь к конфигурационному файлу
CONFIG_FILE = 'lyssa_config.json'

# Допустимые уровни доступа
VALID_ACCESS_LEVELS = ["owner", "admin", "all"]

# Функция для загрузки конфигурации из файла
def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        # Если файл не существует, создаём его с уровнем доступа "owner"
        default_config = {"access_level": "owner"}
        save_config(default_config)
        return default_config
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            config = json.load(f)
            if "access_level" not in config:
                config["access_level"] = "owner"
                save_config(config)
            return config
        except json.JSONDecodeError:
            logger.error("Ошибка при чтении конфигурационного файла. Создаётся новый файл.")
            default_config = {"access_level": "owner"}
            save_config(default_config)
            return default_config

# Функция для сохранения конфигурации в файл
def save_config(config: dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    logger.info(f"Конфигурация сохранена: {config}")

# Функция для получения текущего уровня доступа
def get_access_level() -> str:
    config = load_config()
    return config.get("access_level", "owner")

# Синхронная функция для установки нового уровня доступа
def set_access_level(level: str):
    if level not in VALID_ACCESS_LEVELS:
        logger.error(f"Недопустимый уровень доступа: {level}")
        raise ValueError("Уровень доступа должен быть 'owner', 'admin' или 'all'.")

    config = load_config()
    config["access_level"] = level
    save_config(config)
    logger.info(f"Уровень доступа установлен на: {level}")

# Функция для проверки прав пользователя
async def has_permission(update: Update, context: ContextTypes.DEFAULT_TYPE, required_level: str = "admin") -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    current_level = get_access_level()

    if current_level == "all":
        return True  # Все пользователи имеют доступ

    try:
        user_status = await context.bot.get_chat_member(chat_id, user_id)
        if current_level == "admin" and user_status.status in ["administrator", "creator"]:
            return True
        if current_level == "owner" and user_status.status == "creator":
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке прав пользователя {user_id}: {e}")

    return False

# Обработчик команды /lock
async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получена команда /lock от пользователя {update.effective_user.id}")

    # Проверка прав пользователя
    if not await has_permission(update, context, required_level="admin"):
        logger.warning(f"Пользователь {update.effective_user.id} не имеет прав для выполнения команды /lock")
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    # Проверка наличия аргументов
    if not context.args:
        current_level = get_access_level()
        logger.info(f"Текущий уровень доступа: {current_level}")
        await update.message.reply_text(f"Текущий уровень доступа: {current_level}")
        return

    level = context.args[0].lower()
    logger.info(f"Попытка установить уровень доступа на: {level}")

    # Валидация входных данных
    if level not in VALID_ACCESS_LEVELS:
        logger.warning(f"Недопустимый уровень доступа: {level}")
        await update.message.reply_text("Недопустимый уровень доступа. Допустимые значения: owner, admin, all.")
        return

    # Установка уровня доступа
    try:
        set_access_level(level)  # Синхронный вызов
        await update.message.reply_text(f"Уровень доступа изменен на: {level}")
        logger.info(f"Уровень доступа успешно изменен на: {level}")
    except ValueError as e:
        await update.message.reply_text(str(e))
        logger.error(f"Не удалось изменить уровень доступа: {e}")