FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода сервиса
COPY app/ ./app/

# Создание директории для моделей
RUN mkdir -p /app/models

# Переменные окружения
ENV MODEL_PATH=/app/models/best.pt
ENV PORT=8000
# Исправление для PyTorch 2.6+ (разрешить загрузку YOLOv8 моделей)
ENV TORCH_ALLOW_UNSAFE_LOAD=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Запуск сервиса
CMD ["python", "-m", "app.main"]

