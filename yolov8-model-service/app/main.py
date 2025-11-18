"""
YOLOv8 Model Service - Микросервис для детекции объектов
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os

from app.core.config import get_settings
from app.api import predict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="YOLOv8 Model Service",
    description="Микросервис для детекции элементов ЛЭП",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(predict.router, tags=["predict"])

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "YOLOv8 Model Service is running",
        "service": "yolov8-model-service",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run(app, host=settings.HOST, port=port)

