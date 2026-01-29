"""Конфигурация бота"""
import os

# Токен Telegram-бота от @BotFather
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Папка для временных файлов
TEMP_DIR = os.environ.get("TEMP_DIR", "/tmp/video_downloads")

# Время хранения файлов (в днях)
FILE_RETENTION_DAYS = int(os.environ.get("FILE_RETENTION_DAYS", 2))
