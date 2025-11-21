FROM python:3.11-slim as base

WORKDIR /app

# Установка системных зависимостей и шрифтов с поддержкой кириллицы
RUN apt-get update && apt-get install -y \
    curl \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY app/ ./app/

# Production stage
FROM base as production

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
