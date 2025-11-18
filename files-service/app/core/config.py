from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres-files:5432/files_db"

    # Storage
    STORAGE_PATH: str = "/app/storage"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Allowed file types
    ALLOWED_JSON_EXTENSIONS: set = {".json"}
    ALLOWED_XSD_EXTENSIONS: set = {".xsd", ".xml"}
    ALLOWED_TEST_DATA_EXTENSIONS: set = {".json", ".txt"}
    ALLOWED_VM_EXTENSIONS: set = {".vm", ".txt"}
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()

