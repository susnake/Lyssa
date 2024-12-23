# modules/config.py

import logging
import os
import json

logger = logging.getLogger(__name__)

CONFIG_FILE = 'lyssa_config.json'  # Убедитесь, что путь корректный

DEFAULT_CONFIG = {
    "access_level": "owner",
    "banUsers": False,  # False: кикать, True: банить
    "time_limit": 60  # Пример другой настройки
    # Добавьте другие ключи конфигурации по необходимости
}


def load_config() -> dict:
    """Загружает конфигурацию из файла. Если файл отсутствует, создаёт его с настройками по умолчанию."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("Файл конфигурации не найден. Создаётся новый файл с настройками по умолчанию.")
        save_config(DEFAULT_CONFIG)  # Создаём файл с настройками по умолчанию
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
        logger.info("Конфигурация успешно загружена.")
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        return DEFAULT_CONFIG.copy()

    # Проверяем наличие ключей и добавляем отсутствующие
    updated = False
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = default_value
            logger.info(f"Ключ '{key}' добавлен в конфигурацию с значением по умолчанию: {default_value}")
            updated = True

    if updated:
        save_config(config)
        logger.info("Конфигурационный файл обновлён с добавлением отсутствующих ключей.")

    return config.copy()


def save_config(config: dict):
    """Сохраняет конфигурацию в файл."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info("Конфигурационный файл успешно сохранён.")
    except Exception as e:
        logger.error(f"Не удалось сохранить конфигурационный файл: {e}")
