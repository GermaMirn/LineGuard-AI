from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # JWT настройки
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # База данных
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres-db"
    DB_HOST: str = "postgres-db"

    # Email настройки (для уведомлений)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()

