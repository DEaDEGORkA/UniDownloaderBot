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

# Создаём директорию для временных файлов
RUN mkdir -p /tmp/video_downloads

# Переменные окружения
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "main.py"]