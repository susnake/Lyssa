from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ContextTypes
)
import logging
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import string
import json
import io
from lock import has_permission

logger = logging.getLogger(__name__)
# Список фруктов с эмоджи
ALL_FRUITS = [
    "🍎", "🍌", "🍇", "🍓", "🍍",
    "🥭", "🥝", "🍑", "🍒", "🍉",
    "🍋", "🍈", "🍐", "🍊", "🍏",
    "🥥", "🍅"
]

# Конфигурация капчи по умолчанию
DEFAULT_CONFIG = {
    "captcha_type": "button",  # Возможные: button, math, fruits, image
    "time_limit": 60,  # Время на прохождение капчи в секундах
    "custom_captcha_message": "Пожалуйста, подтвердите, что вы не бот!",
    "button_text": "Я не бот!"
}

CONFIG_FILE = "lyssa_config.json"


def load_config():
    """Загружает конфигурацию из файла. Если файл отсутствует, создаёт его с настройками по умолчанию."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("Файл конфигурации не найден. Создаётся новый файл с настройками по умолчанию.")
        save_config(DEFAULT_CONFIG)  # Создаём файл с настройками по умолчанию
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
        logger.info("Конфигурация успешно загружена.")
        return config
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        return DEFAULT_CONFIG


def save_config(config):
    """Сохраняет конфигурацию в файл."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
        logger.info("Конфигурация успешно сохранена.")
    except IOError as e:
        logger.error(f"Ошибка при сохранении конфигурации: {e}")


# Инициализация конфигурации
bot_config = load_config()
# Хранилище для капч
verified_users = set()
user_math_captcha = {}  # Для math-капчи
user_captcha_code = {}  # Для image-капчи
captcha_jobs = {}  # Для отслеживания задач по капчам
user_captcha_messages = {}  # Для отслеживания message_id капчи и предупреждений


def generate_captcha_code(length=5):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def generate_captcha_image(
    text,
    font_path='Fonts/arial.ttf',  # Убедитесь, что путь к шрифту корректен
    size=(200, 80),  # Передаем размеры изображения как параметр
    noise_points=50,
    blur_intensity=0
):
    width, height = size  # Используем переданный параметр size
    background_color = (255, 255, 255)
    font_size = 36

    # Создаём новое изображение
    image = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(image)

    # Загружаем шрифт
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        logger.warning("Шрифт не найден. Используется стандартный шрифт.")

    # Добавляем текст на изображение
    text_color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    draw.text((text_x, text_y), text, font=font, fill=text_color)

    # Добавляем случайные линии для усложнения капчи
    for _ in range(5):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        line_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.line([start, end], fill=line_color, width=2)

    # Добавляем шум
    for _ in range(noise_points):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # Применяем фильтр размытия
    for _ in range(blur_intensity):
        image = image.filter(ImageFilter.BLUR)

    # Сохраняем изображение в байтовый поток
    byte_io = io.BytesIO()
    image.save(byte_io, 'PNG')
    byte_io.seek(0)

    return byte_io


async def captcha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меняет тип капчи."""
    # Загружаем текущую конфигурацию
    if not await has_permission(update, context):
        await update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
        return
    global bot_config
    bot_config = load_config()

    if context.args:
        new_type = context.args[0].lower()
        if new_type in ["button", "math", "fruits", "image"]:
            bot_config["captcha_type"] = new_type
            save_config(bot_config)  # Сохраняем изменения
            await update.message.reply_text(f"Тип капчи установлен: {new_type}")
            logger.info(f"Тип капчи изменён на: {new_type}")

            # Показываем пример капчи
            if new_type == "button":
                keyboard = [[InlineKeyboardButton("Пример кнопки", callback_data="example_button")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Вот пример капчи кнопкой:", reply_markup=reply_markup)
            elif new_type == "math":
                # Пример математической капчи
                expression = "3 + 5 = ?"
                buttons = [
                    [InlineKeyboardButton("8", callback_data="example_math_correct")],
                    [InlineKeyboardButton("7", callback_data="example_math_wrong")]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                await update.message.reply_text(f"Вот пример math капчи: {expression}", reply_markup=reply_markup)
            elif new_type == "fruits":
                # Пример фруктовой капчи
                example_fruits = ["🍎", "🍌", "🍇", "🍍"]
                correct_fruit = "🍍"
                buttons = [
                    [InlineKeyboardButton(fruit,
                                          callback_data="example_fruit_correct" if fruit == correct_fruit else "example_fruit_wrong")]
                    for fruit in example_fruits
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                await update.message.reply_text("Вот пример капчи с фруктами: выберите 🍍", reply_markup=reply_markup)
            elif new_type == "image":
                # Генерация кода для примера
                code = generate_captcha_code(length=5)
                captcha_image = generate_captcha_image(code)

                # Генерация кнопок для примера (одна строка)
                buttons = [
                    InlineKeyboardButton(char, callback_data=f"example_image_{char}")
                    for char in random.sample(code, len(code))
                ]
                reply_markup = InlineKeyboardMarkup([buttons])  # Одной строкой

                # Отправка изображения с кнопками
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=InputFile(captcha_image, filename="example_captcha.png"),
                    caption="Вот пример image капчи. Нажмите кнопки в порядке символов на изображении.",
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text("Доступные типы капчи: button, math, fruits, image.")
    else:
        await update.message.reply_text(f"Текущий тип капчи: {bot_config['captcha_type']}")


async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает новых участников чата."""
    chat_id = update.effective_chat.id
    for user in update.message.new_chat_members:
        if user.id in verified_users:
            logger.info(f"Пользователь {user.id} уже верифицирован.")
            continue

        captcha_type = bot_config["captcha_type"]
        logger.info(f"Обработка капчи для пользователя {user.id} типа {captcha_type}")

        # Получаем имя пользователя для персонализации сообщений
        if user.username:
            user_display = f"@{user.username}"
        else:
            user_display = user.full_name

        # Очистка предыдущих данных, если таковые имеются
        if user.id in user_math_captcha:
            del user_math_captcha[user.id]
            logger.info(f"Удалены предыдущие данные math капчи для пользователя {user.id}.")
        if user.id in user_captcha_code:
            del user_captcha_code[user.id]
            logger.info(f"Удалены предыдущие данные image капчи для пользователя {user.id}.")

        if captcha_type == "button":
            try:
                # Загружаем актуальную конфигурацию
                config = load_config()
                time_limit = config.get("time_limit", DEFAULT_CONFIG["time_limit"])

                # Кнопка "Я не бот!"
                keyboard = [[InlineKeyboardButton(bot_config["button_text"], callback_data="captcha_ok")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{user_display}, {bot_config['custom_captcha_message']}, у вас есть {time_limit}",
                    reply_markup=reply_markup
                )
                logger.info(f"Сообщение капчи отправлено пользователю {user.id}.")

                # Сохраняем message_id основного сообщения капчи
                if user.id not in user_captcha_messages:
                    user_captcha_messages[user.id] = {}
                user_captcha_messages[user.id]['captcha'] = message.message_id

                # Ограничение прав пользователя
                await restrict_user(context, chat_id, user.id)
            except Exception as e:
                logger.error(f"Ошибка при отправке капчи для пользователя {user.id}: {e}")

        elif captcha_type == "math":
            try:
                # Математическая капча (сложение или вычитание)
                num1 = random.randint(1, 20)
                num2 = random.randint(1, 20)
                operation = random.choice(['+', '-'])
                expression = f"{num1} {operation} {num2} = ?"
                answer = num1 + num2 if operation == '+' else num1 - num2
                user_math_captcha[user.id] = answer

                # Генерация вариантов ответов
                possible_answers = set()
                possible_answers.add(answer)
                while len(possible_answers) < 4:
                    wrong_answer = answer + random.choice([-3, -2, -1, 1, 2, 3])
                    if wrong_answer > 0:
                        possible_answers.add(wrong_answer)
                possible_answers = list(possible_answers)
                random.shuffle(possible_answers)

                # Создание кнопок
                buttons = []
                for ans in possible_answers:
                    if ans == answer:
                        buttons.append([InlineKeyboardButton(str(ans), callback_data="captcha_math_ok")])
                    else:
                        buttons.append([InlineKeyboardButton(str(ans), callback_data="captcha_math_fail")])
                reply_markup = InlineKeyboardMarkup(buttons)

                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{user_display}, {expression}\nВыберите правильный ответ:",
                    reply_markup=reply_markup
                )
                logger.info(f"Сообщение math капчи отправлено пользователю {user.id}.")

                # Сохраняем message_id основного сообщения капчи
                if user.id not in user_captcha_messages:
                    user_captcha_messages[user.id] = {}
                user_captcha_messages[user.id]['captcha'] = message.message_id

                # Ограничение прав пользователя
                await restrict_user(context, chat_id, user.id)
            except Exception as e:
                logger.error(f"Ошибка при отправке math капчи для пользователя {user.id}: {e}")

        elif captcha_type == "fruits":
            try:
                # Капча с фруктами
                if len(ALL_FRUITS) < 4:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Недостаточно фруктов для капчи."
                    )
                    logger.error("Недостаточно фруктов для капчи.")
                    return

                chosen_emojis = random.sample(ALL_FRUITS, 4)
                correct_emoji = random.choice(chosen_emojis)
                instruction_text = f"{user_display}, выберите фрукт {correct_emoji}, чтобы подтвердить, что вы не бот!"
                buttons = []
                for emoji in chosen_emojis:
                    if emoji == correct_emoji:
                        buttons.append([InlineKeyboardButton(emoji, callback_data="captcha_fruit_ok")])
                    else:
                        buttons.append([InlineKeyboardButton(emoji, callback_data="captcha_fruit_fail")])
                random.shuffle(buttons)
                reply_markup = InlineKeyboardMarkup(buttons)

                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=instruction_text,
                    reply_markup=reply_markup
                )
                logger.info(f"Сообщение фруктовой капчи отправлено пользователю {user.id}.")

                # Сохраняем message_id основного сообщения капчи
                if user.id not in user_captcha_messages:
                    user_captcha_messages[user.id] = {}
                user_captcha_messages[user.id]['captcha'] = message.message_id

                # Ограничение прав пользователя
                await restrict_user(context, chat_id, user.id)
            except Exception as e:
                logger.error(f"Ошибка при отправке фруктовой капчи для пользователя {user.id}: {e}")

        elif captcha_type == "image":
            try:
                code = generate_captcha_code()
                user_captcha_code[user.id] = {"code": code, "current_index": 0}

                # Генерация изображения капчи
                font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
                captcha_image = generate_captcha_image(code, font_path=font_path, size=(200, 80))

                # Генерация кнопок
                buttons = [
                    InlineKeyboardButton(char, callback_data=f"captcha_image_{char}")
                    for char in random.sample(code, len(code))
                ]
                reply_markup = InlineKeyboardMarkup([buttons])

                # Отправка изображения и кнопок
                message = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=InputFile(captcha_image, filename='captcha.png'),
                    caption=f"{user_display}, нажмите кнопки в порядке символов из изображения.",
                    reply_markup=reply_markup
                )
                logger.info(f"Сообщение image капчи отправлено пользователю {user.id}.")

                # Сохраняем message_id капчи
                if user.id not in user_captcha_messages:
                    user_captcha_messages[user.id] = {}
                user_captcha_messages[user.id]['captcha'] = message.message_id

                # Ограничение прав пользователя
                await restrict_user(context, chat_id, user.id)
            except Exception as e:
                logger.error(f"Ошибка при отправке image капчи для пользователя {user.id}: {e}")

        else:
            try:
                # Если тип капчи не распознан
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{user_display}, Тип капчи не установлен или некорректен. Пожалуйста, обратитесь к администратору."
                )
                logger.warning(f"Неизвестный тип капчи: {captcha_type} для пользователя {user.id}")
            except Exception as e:
                logger.error(f"Ошибка при уведомлении пользователя {user.id} о неизвестном типе капчи: {e}")


async def handle_left_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает события ухода или кика пользователей из чата."""
    chat_id = update.effective_chat.id
    left_member = update.message.left_chat_member
    if left_member:
        user_id = left_member.id
        logger.info(f"Пользователь {left_member.username or left_member.full_name} покинул(а) группу.")

        # Отменяем запланированные задания капчи
        await cancel_captcha_jobs(context, user_id, chat_id)

        # Удаляем сообщение капчи, если оно существует
        message_info = user_captcha_messages.get(user_id)
        if message_info:
            for key, message_id in message_info.items():
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    logger.info(f"Сообщение '{key}' капчи для пользователя {user_id} удалено.")
                except Exception as e:
                    logger.error(f"Не удалось удалить сообщение '{key}' капчи для пользователя {user_id}: {e}")
            del user_captcha_messages[user_id]


async def restrict_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Ограничивает права пользователя на время прохождения капчи."""
    try:
        # Ограничиваем отправку сообщений и медиа
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions={
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False,
            },
        )
        logger.info(f"Права пользователя {user_id} ограничены.")
    except Exception as e:
        logger.error(f"Не удалось ограничить права пользователя {user_id}: {e}")
        return

    # Загружаем актуальную конфигурацию
    config = load_config()
    time_limit = config.get("time_limit", DEFAULT_CONFIG["time_limit"])

    # Запланировать предупреждение через половину времени лимита
    warning_time = time_limit // 2
    job_warning = context.job_queue.run_once(
        callback=send_warning,
        when=warning_time,
        data={"chat_id": chat_id, "user_id": user_id},
        name=f"warning_{user_id}"
    )
    logger.info(f"Предупреждение для пользователя {user_id} запланировано через {warning_time} секунд.")

    # Запланировать кик через полный лимит времени
    job_kick = context.job_queue.run_once(
        callback=kick_user,
        when=time_limit,
        data={"chat_id": chat_id, "user_id": user_id},
        name=f"kick_{user_id}"
    )
    logger.info(f"Кик для пользователя {user_id} запланирован через {time_limit} секунд.")

    # Сохраняем задания для возможного отмена
    captcha_jobs[user_id] = {
        'warning': job_warning,
        'kick': job_kick,
    }
    logger.info(
        f"Капча для пользователя {user_id} запланирована: предупреждение через {warning_time} секунд, кик через {time_limit} секунд.")


async def send_warning(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет предупреждение пользователю о оставшемся времени."""
    job = context.job
    data = job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]

    try:
        # Загружаем актуальную конфигурацию
        config = load_config()
        time_limit = config.get("time_limit", DEFAULT_CONFIG["time_limit"])

        # Вычисляем оставшееся время до истечения лимита
        warning_time = time_limit // 2

        user = await context.bot.get_chat_member(chat_id, user_id)
        if user.status in ["left", "kicked", "restricted"]:
            logger.info(f"Пользователь {user_id} уже покинул чат. Предупреждение не отправляется.")
            return

        user_full_name = user.user.full_name
        mention = f"@{user.user.username}" if user.user.username else user_full_name

        warning_message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"Пользователь {mention}: у вас осталось {warning_time} секунд, чтобы пройти капчу.",
        )
        logger.info(f"Отправлено предупреждение пользователю {user_id}.")

        # Сохраняем message_id предупреждения
        if user_id not in user_captcha_messages:
            user_captcha_messages[user_id] = {}
        user_captcha_messages[user_id]['warning'] = warning_message.message_id

    except Exception as e:
        logger.error(f"Не удалось отправить предупреждение пользователю {user_id}: {e}")


async def kick_user(context: ContextTypes.DEFAULT_TYPE):
    """Банит пользователя из группы за не прохождение капчи."""
    job = context.job
    data = job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        if user.status in ["left", "kicked"]:
            logger.info(f"Пользователь {user_id} уже покинул чат. Кик не требуется.")
            return

        # Используем ban_chat_member вместо kick_chat_member
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        user = await context.bot.get_chat_member(chat_id, user_id)
        user_full_name = user.user.full_name
        mention = f"@{user.user.username}" if user.user.username else user_full_name

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Пользователь {mention} был кикнут за не прохождение капчи.",
        )
        logger.info(f"Пользователь {user_id} кикнут из чата.")
    except Exception as e:
        logger.error(f"Не удалось кикнуть пользователя {user_id}: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки капчи."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user_id = query.from_user.id
    chat_id = query.message.chat.id
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        user_full_name = user.user.full_name
        mention = f"@{user.user.username}" if user.user.username else user_full_name
    except Exception as e:
        logger.error(f"Не удалось получить информацию о пользователе {user_id}: {e}")
        mention = f"<@{user_id}>"

    if data == "captcha_ok":
        verified_users.add(user_id)
        await query.edit_message_text(f"{mention}, вы успешно прошли проверку!")
        logger.info(f"Пользователь {user_id} успешно прошёл капчу.")
        await cancel_captcha_jobs(context, user_id, chat_id)

    elif data == "captcha_math_ok":
        verified_users.add(user_id)
        await query.edit_message_text(f"{mention}, верно! Добро пожаловать!")
        logger.info(f"Пользователь {user_id} успешно прошёл math капчу.")
        await cancel_captcha_jobs(context, user_id, chat_id)

    elif data == "captcha_math_fail":
        await query.edit_message_text(f"{mention}, неверный ответ! Вы будете кикнуты.")
        logger.info(f"Пользователь {user_id} неверно ответил на math капчу.")
        await kick_user_immediately(context, chat_id, user_id)

    elif data == "captcha_fruit_ok":
        verified_users.add(user_id)
        await query.edit_message_text(f"{mention}, верно! Добро пожаловать!")
        logger.info(f"Пользователь {user_id} успешно прошёл фруктовую капчу.")
        await cancel_captcha_jobs(context, user_id, chat_id)

    elif data == "captcha_fruit_fail":
        await query.edit_message_text(f"{mention}, неправильно! Вы будете кикнуты.")
        logger.info(f"Пользователь {user_id} неправильно ответил на фруктовую капчу.")
        await kick_user_immediately(context, chat_id, user_id)

    elif data.startswith("captcha_image_"):
        char_clicked = data.split("_")[-1]
        user_captcha_info = user_captcha_code.get(user_id, {})
        if not user_captcha_info:
            await query.edit_message_caption("Ошибка! Код капчи не найден.")
            logger.warning(f"Капча для пользователя {user_id} отсутствует.")
            return

        expected_code = user_captcha_info["code"]
        current_index = user_captcha_info.get("current_index", 0)

        if char_clicked == expected_code[current_index]:
            user_captcha_info["current_index"] += 1
            if user_captcha_info["current_index"] == len(expected_code):
                verified_users.add(user_id)
                await query.edit_message_caption("Капча успешно пройдена! Добро пожаловать!")
                logger.info(f"Пользователь {user_id} успешно прошёл image капчу.")
                await cancel_captcha_jobs(context, user_id, chat_id)
            else:
                await query.answer("Верно! Продолжайте.")
        else:
            await query.edit_message_caption("Неправильный ввод символа! Вы будете удалены.")
            logger.info(f"Пользователь {user_id} ввёл неверный символ: {char_clicked}")
            await kick_user_immediately(context, chat_id, user_id)

    elif data == "captcha_math_fail":
        # Неправильный ответ на math капчу
        await query.edit_message_text(f"{mention}, неверный ответ! Вы будете кикнуты.")
        logger.info(f"Пользователь {user_id} неверно ответил на math капчу.")
        await kick_user_immediately(context, chat_id, user_id)

    elif data == "captcha_fruit_ok":
        # Правильный фрукт
        verified_users.add(user_id)
        await query.edit_message_text(f"{mention}, верно! Добро пожаловать!")
        logger.info(f"Пользователь {user_id} успешно прошёл фруктовую капчу.")
        # Отменяем задачи по капче
        await cancel_captcha_jobs(context, user_id, chat_id)

    elif data == "captcha_fruit_fail":
        # Неправильный фрукт
        await query.edit_message_text(f"{mention}, неправильно! Вы будете кикнуты.")
        logger.info(f"Пользователь {user_id} неправильно ответил на фруктовую капчу.")
        await kick_user_immediately(context, chat_id, user_id)


async def cancel_captcha_jobs(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Отменяет запланированные задания капчи и восстанавливает права пользователя."""
    jobs = captcha_jobs.get(user_id, {})
    for job_key, job in jobs.items():
        try:
            job.schedule_removal()
            logger.info(f"Задание '{job_key}' для пользователя {user_id} запланировано на удаление.")
        except Exception as e:
            logger.warning(f"Не удалось отменить задание '{job_key}' для пользователя {user_id}: {e}")
    captcha_jobs.pop(user_id, None)

    # Удаляем все связанные сообщения капчи
    message_info = user_captcha_messages.get(user_id, {})
    for key, message_id in message_info.items():
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"Сообщение '{key}' капчи для пользователя {user_id} удалено.")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение '{key}' капчи для пользователя {user_id}: {e}")
    user_captcha_messages.pop(user_id, None)

    # Проверяем статус пользователя
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        if user.status == "kicked":
            logger.info(f"Пользователь {user_id} находится в черном списке чата. Восстановление прав отменено.")
            return
        elif user.status == "left":
            logger.info(f"Пользователь {user_id} покинул чат. Восстановление прав не требуется.")
            return

        # Восстанавливаем права пользователя, если он всё ещё в чате
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
            },
        )
        logger.info(f"Права пользователя {user_id} восстановлены.")
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса пользователя {user_id}: {e}")

    # Очистка дополнительных данных капчи
    if user_id in user_math_captcha:
        del user_math_captcha[user_id]
        logger.info(f"Удалены данные math капчи для пользователя {user_id}.")
    if user_id in user_captcha_code:
        del user_captcha_code[user_id]
        logger.info(f"Удалены данные image капчи для пользователя {user_id}.")

    # Удаляем пользователя из verified_users, если он там есть
    if user_id in verified_users:
        verified_users.remove(user_id)
        logger.info(f"Пользователь {user_id} удалён из verified_users.")

    # Восстанавливаем права пользователя
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
            },
        )
        logger.info(f"Права пользователя {user_id} восстановлены.")
    except Exception as e:
        logger.error(f"Не удалось восстановить права пользователя {user_id}: {e}")


async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для капчи 'math' и 'image'."""
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    chat_id = update.effective_chat.id

    # Проверка на math-капчу
    if user_id in user_math_captcha:
        expected_answer = user_math_captcha[user_id]
        try:
            user_answer = int(update.message.text.strip())
            if user_answer == expected_answer:
                verified_users.add(user_id)
                await update.message.reply_text("Капча пройдена, добро пожаловать!")
                logger.info(f"Пользователь {user_id} успешно прошёл math капчу через текстовое сообщение.")
                del user_math_captcha[user_id]
                # Отменяем задачи по капче
                await cancel_captcha_jobs(context, user_id, chat_id)
            else:
                await update.message.reply_text("Неверный ответ! Вы будете кикнуты.")
                logger.info(f"Пользователь {user_id} ввёл неверный ответ на math капчу.")
                await kick_user_immediately(context, chat_id, user_id)
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите числовой ответ.")
            logger.info(f"Пользователь {user_id} ввёл некорректный ответ на math капчу.")
            await kick_user_immediately(context, chat_id, user_id)
        return

    # Проверка на image-капчу (изображение)
    if user_id in user_captcha_code:
        expected_code = user_captcha_code[user_id]
        user_code = update.message.text.strip()
        if user_code == expected_code:
            verified_users.add(user_id)
            await update.message.reply_text("Капча пройдена, добро пожаловать!")
            logger.info(f"Пользователь {user_id} успешно прошёл image капчу через текстовое сообщение.")
            del user_captcha_code[user_id]
            # Отменяем задачи по капче
            await cancel_captcha_jobs(context, user_id, chat_id)
        else:
            await update.message.reply_text("Неверный код! Вы будете кикнуты.")
            logger.info(f"Пользователь {user_id} ввёл неверный код на image капчу.")
            await kick_user_immediately(context, chat_id, user_id)
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки, возникающие в хендлерах."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)