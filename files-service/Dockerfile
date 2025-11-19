# Base stage
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage && chmod 755 /app/storage

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Development stage
FROM base AS development
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload

# Production stage
FROM base AS production
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8006

