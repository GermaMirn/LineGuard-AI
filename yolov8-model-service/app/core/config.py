from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Model settings
    MODEL_PATH: str = "/app/models/best.pt"
    DEFAULT_CONF_THRESHOLD: float = 0.25
    
    # Service settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Image processing settings
    MAX_FILE_SIZE_MB: int = 100  # Максимальный размер файла в MB
    MAX_FILE_SIZE_STANDARD_MB: int = 50  # Максимальный размер для стандартных форматов
    MAX_RESOLUTION: int = 7680  # Максимальное разрешение (8K)
    
    # Supported formats
    SUPPORTED_IMAGE_FORMATS: set = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/tiff', 'image/tif',
        'image/x-dji', 'image/x-autel', 'application/octet-stream'
    }
    
    SUPPORTED_EXTENSIONS: set = {
        '.jpg', '.jpeg', '.png', '.tiff', '.tif', 
        '.dng', '.raw', '.cr2', '.nef', '.arw'
    }
    
    # RAW formats that require special processing
    RAW_EXTENSIONS: set = {'.raw', '.dng', '.cr2', '.nef', '.arw'}

    class Config:
        env_file = ".env"
        case_sensitive = False

def get_settings() -> Settings:
    return Settings()

