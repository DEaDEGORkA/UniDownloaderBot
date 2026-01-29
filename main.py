"""Telegram-бот для скачивания видео с помощью yt-dlp"""
import os
import logging
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

from config import TELEGRAM_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Отправь мне ссылку на видео, и я скачаю его и отправлю тебе."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "Просто отправь ссылку на видео, и я скачаю его и отправлю обратно.\n"
        "Поддерживаются YouTube и другие платформы."
    )


def download_video(url: str) -> str | None:
    """
    Скачивает видео по URL и возвращает путь к файлу.
    Возвращает None в случае ошибки.
    """
    # Создаём временную директорию для скачивания
    temp_dir = tempfile.mkdtemp()
    
    # Настройки yt-dlp
    ydl_opts = {
        "format": "best",  # Лучшее качество
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", "video")
            video_ext = info.get("ext", "mp4")
            
            # Ищем скачанный файл
            video_path = Path(temp_dir).glob(f"*.{video_ext}").__next__()
            return str(video_path)
    except Exception as e:
        logger.error(f"Ошибка при скачивании видео: {e}")
        return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений со ссылками"""
    url = update.message.text.strip()
    
    # Проверяем, что это ссылка (упрощённая проверка)
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Пожалуйста, отправьте корректную ссылку на видео.")
        return
    
    # Отправляем сообщение о начале загрузки
    processing_message = await update.message.reply_text("⏳ Скачиваю видео... Это может занять некоторое время.")
    
    # Скачиваем видео
    video_path = download_video(url)
    
    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path)
        
        # Telegram ограничение на размер файла - 50 МБ для большинства ботов
        # Если файл больше, предупреждаем пользователя
        if file_size > 50 * 1024 * 1024:
            await processing_message.edit_text(
                f"⚠️ Видео слишком большое ({file_size / (1024*1024):.1f} МБ).\n"
                "Telegram не может отправить файлы больше 50 МБ."
            )
            os.remove(video_path)
            return
        
        try:
            await processing_message.edit_text("📤 Отправляю видео...")
            await update.message.reply_video(
                video=open(video_path, "rb"),
                caption=f"Ваше видео: {Path(video_path).stem}"
            )
            await processing_message.delete()
        except Exception as e:
            logger.error(f"Ошибка при отправке видео: {e}")
            await processing_message.edit_text("Ошибка при отправке видео. Попробуйте позже.")
        finally:
            # Удаляем временный файл
            if os.path.exists(video_path):
                os.remove(video_path)
    else:
        await processing_message.edit_text(
            "❌ Не удалось скачать видео. Проверьте ссылку и попробуйте снова."
        )


def main():
    """Запуск бота"""
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )

    logger.info("Запуск бота...")
    application.run_polling()


if __name__ == "__main__":
    main()