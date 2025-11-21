from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Files service URL
    FILES_SERVICE_URL: str = "http://files-service:8000"
    
    # Service settings
    SERVICE_NAME: str = "annotation-service"
    SERVICE_VERSION: str = "1.0.0"
    
    # Image processing settings
    BBOX_COLOR: tuple = (255, 0, 0)  # Red color for bbox
    BBOX_THICKNESS: int = 3  # Thickness of bbox lines
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    return Settings()


