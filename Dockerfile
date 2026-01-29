FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для yt-dlp (ffmpeg и т.д.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/tmp/video_downloads
ENV FILE_RETENTION_DAYS=2

# Создаём директорию для скачанных файлов
RUN mkdir -p /tmp/video_downloads

# Запуск бота
CMD ["python", "main.py"]