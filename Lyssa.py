import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
import logging
from captcha import (
    load_config, save_config, captcha_command, handle_new_members,
    handle_left_members, button_callback, handle_text_messages, kick_user, Update
)
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from banUsers import set_ban_mode, ban_or_kick_user
from lock import set_access_level, has_permission

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваш токен (после перегенерации)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Рекомендуется хранить токен в переменной окружения

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не установлена. Пожалуйста, установите переменную окружения.")
    exit(1)


async def some_command(update, context):
    if not await has_permission(update, context, "admin"):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return
    # Основная логика команды
    await update.message.reply_text("Команда выполнена успешно.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return
    """Отправляет справочное сообщение."""
    help_text = (
        "/help — показать это сообщение\n"
        "/captcha <type> — сменить тип капчи (button, math, fruits, image)\n"
        "/timeLimit <seconds> — изменить время для капчи\n"
        "/lock — команды только для админов\n"
        "/restrict — запрет медиа для новичков 24ч\n"
        "/deleteEntryMessages — удалять ли сообщения о входе\n"
        "/greeting — включить/выключить приветствие\n"
        "/trust — ответить на сообщение пользователя, которого не нужно проверять\n"
        "/ban <user> <reason> — забанить пользователя\n"
        "/strict — вкл/выкл strict режим\n"
        "/customCaptchaMessage <message> — своё сообщение капчи\n"
        "/deleteGreetingTime <seconds> — время удаления приветствия\n"
        "/banUsers — банить/кикать не прошедших капчу\n"
        "/deleteEntryOnKick — удалять ли сообщение о входе при кике\n"
        "/cas — вкл/выкл Combot Anti-Spam\n"
        "/underAttack — вкл/выкл режим автокика\n"
        "/noAttack — отключить бота\n"
        "/noChannelLinks — вкл/выкл удаление ссылок на каналы\n"
        "/viewConfig — показать настройки\n"
        "/buttonText <text> — изменить текст кнопки капчи\n"
        "/allowInvitingBots — вкл/выкл приглашение ботов\n"
        "/greetingButtons <text1>; ... — кнопки приветствия\n"
        "/setConfig key=value ... — настроить бота одним сообщением\n"
        "/banForFastRepliesToPosts — вкл/выкл бан за быстрые ответы\n"
        "/restrictTime <hours> — время рестрикта медиа\n"
        "/comments <N> — показать и упомянуть пользователей с меньше N сообщениями\n"
        "/link <link or ID> — лог-чат\n"
    )
    await update.message.reply_text(help_text)


async def ban_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для изменения режима бана/кика."""
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return

    if context.args:
        mode = context.args[0].lower()
        if mode == "true":
            set_ban_mode(True)
            await update.message.reply_text("Режим изменён: пользователи будут добавляться в черный список.")
        elif mode == "false":
            set_ban_mode(False)
            await update.message.reply_text("Режим изменён: пользователи будут кикаться.")
        else:
            await update.message.reply_text("Используйте: /banUsers true или /banUsers false.")
    else:
        config = load_config()
        current_mode = "бан" if config["banUsers"] else "кик"
        await update.message.reply_text(f"Текущий режим: {current_mode}.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки, возникающие в хендлерах."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Получаем текст ошибки
    error_message = str(context.error)

    # Логируем подробности ошибки
    if update:
        logger.info(f"Update content: {update}")

    # Пытаемся отправить сообщение в чат, если возможно
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Произошла ошибка: {error_message}. Пожалуйста, повторите попытку позже.",
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке в чат: {e}")


def main():
    """Запуск бота."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд и сообщений
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("captcha", captcha_command))
    app.add_handler(CommandHandler("banUsers", ban_users_command))
    app.add_handler(CommandHandler("lock", set_access_level))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_members))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    # Обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info("Бот запущен и ожидает новых сообщений.")
    # Запуск бота
    app.run_polling()


if __name__ == "__main__":
    main()