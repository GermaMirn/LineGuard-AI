from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # JWT настройки
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"

    # Локальный режим
    BACKEND_LOCAL: bool = False

    # Сервисы
    AUTH_SERVICE_URL: str = "http://auth-service:8002"
    FILES_SERVICE_URL: str = "http://files-service:8006"
    YOLOV8_SERVICE_URL: str = "http://yolov8-model-service:8000"
    ANNOTATION_SERVICE_URL: str = "http://annotation-service:8000"

    # Аналитика / задачи (используем общую БД postgres-db)
    ANALYSIS_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres-db:5432/postgres-db"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    ANALYSIS_QUEUE_NAME: str = "analysis_tasks"
    ANALYSIS_UPDATES_EXCHANGE: str = "analysis_updates"
    MAX_BATCH_FILES: int = 50000
    MAX_BATCH_SIZE_BYTES: int = 10 * 1024 * 1024 * 1024  # 10 GB
    PREVIEW_LIMIT: int = 10
    MAX_YOLO_FILE_SIZE_MB: int = 512
    UPLOAD_PREVIEW_LIMIT: int = 10  # Сколько файлов сохранять как превью при загрузке

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()

