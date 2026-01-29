"""Telegram-бот для скачивания видео с помощью yt-dlp"""
import os
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

from config import TELEGRAM_TOKEN, TEMP_DIR, FILE_RETENTION_DAYS

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


def cleanup_old_files():
    """Удаляет файлы старше FILE_RETENTION_DAYS дней"""
    temp_path = Path(TEMP_DIR)
    if not temp_path.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=FILE_RETENTION_DAYS)
    deleted_count = 0
    freed_space = 0

    for file_path in temp_path.glob("**/*"):
        if file_path.is_file():
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    freed_space += file_size
                    logger.info(f"Удалён старый файл: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {e}")

    if deleted_count > 0:
        logger.info(
            f"Очистка завершена: удалено {deleted_count} файлов, "
            f"освобождено {freed_space / (1024*1024):.2f} МБ"
        )


def download_video(url: str) -> str | None:
    """
    Скачивает видео по URL и возвращает путь к файлу.
    Возвращает None в случае ошибки.
    """
    # Создаём директорию для скачивания, если не существует
    Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

    # Путь к файлу cookies
    cookies_path = os.environ.get("COOKIES_FILE", "/app/cookies.txt")

    # Настройки yt-dlp с поддержкой проблемных сайтов (RedGifs, Cloudflare и т.д.)
    ydl_opts = {
        "format": "best",
        "outtmpl": os.path.join(TEMP_DIR, "%(title)s.%(ext)s"),
        "quiet": False,
        "no_warnings": False,
        # Настройки для Cloudflare и проблемных сайтов
        "extractor_retries": 5,
        "fragment_retries": 5,
        "skip_unavailable_fragments": False,
        "http_chunk_size": 10485760,
        # Заголовки для имитации браузера
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
        # Настройки для работы с Cloudflare
        "geo_bypass": True,
        "nocheckcertificate": False,
    }

    # Если есть файл cookies, используем его
    if os.path.exists(cookies_path):
        ydl_opts["cookies"] = cookies_path
        logger.info(f"Используем cookies из {cookies_path}")
    else:
        logger.info("Файл cookies не найден, используем настройки по умолчанию")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=True)
            video_ext = info.get("ext", "mp4")
            video_title = info.get("title", "video")

            # Ищем скачанный файл
            files = list(Path(TEMP_DIR).glob(f"*.{video_ext}"))
            if files:
                video_path = files[0]
                logger.info(f"Видео '{video_title}' скачано: {video_path}")
                return str(video_path)
            logger.warning(f"Файл видео не найден для '{video_title}'")
            return None
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Ошибка загрузки: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
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
    else:
        await processing_message.edit_text(
            "❌ Не удалось скачать видео. Проверьте ссылку и попробуйте снова."
        )


async def scheduled_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Периодическая очистка старых файлов"""
    logger.info("Запуск плановой очистки файлов...")
    cleanup_old_files()


def cleanup_worker():
    """Фоновый поток для периодической очистки файлов"""
    logger.info("Воркер очистки запущен")
    while True:
        time.sleep(6 * 60 * 60)  # Спим 6 часов
        cleanup_old_files()


def main():
    """Запуск бота"""
    if not TELEGRAM_TOKEN:
        logger.error("Не указан TELEGRAM_TOKEN. Установите переменную окружения.")
        return

    # Запускаем фоновый поток для очистки файлов
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

    # Первичная очистка при старте
    cleanup_old_files()

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