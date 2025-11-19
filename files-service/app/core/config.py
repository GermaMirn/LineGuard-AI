from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres-files:5432/files_db"

    # Storage
    STORAGE_PATH: str = "/app/storage"
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB per file

    # Allowed file types
    ALLOWED_JSON_EXTENSIONS: set = {".json"}
    ALLOWED_XSD_EXTENSIONS: set = {".xsd", ".xml"}
    ALLOWED_TEST_DATA_EXTENSIONS: set = {".json", ".txt"}
    ALLOWED_VM_EXTENSIONS: set = {".vm", ".txt"}
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    ALLOWED_RAW_EXTENSIONS: set = {".dng", ".raw", ".nef", ".cr2", ".arw"}
    ALLOWED_ANALYSIS_RESULT_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}
    ALLOWED_ANALYSIS_PREVIEW_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}
    ALLOWED_ANALYSIS_ARCHIVE_EXTENSIONS: set = {".zip"}

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()

