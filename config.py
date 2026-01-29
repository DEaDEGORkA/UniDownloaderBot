"""Конфигурация бота"""
import os

# Токен Telegram-бота от @BotFather
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Папка для временных файлов
TEMP_DIR = "temp"