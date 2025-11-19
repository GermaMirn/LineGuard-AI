import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, files, predict, analysis
from app.db.session import init_models
from app.schemas.analysis import AnalysisTaskProgress
from app.services.queue import rabbitmq_client
from app.services.websocket_manager import task_ws_manager

app = FastAPI(
    title="BFF Service",
    description="Backend for Frontend Service - API Gateway для мониторинга ЛЭП",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(predict.router, prefix="/api", tags=["predict"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])


async def _updates_consumer() -> None:
    async def handler(payload: dict) -> None:
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Received update payload: {payload}")
            progress = AnalysisTaskProgress(**payload)
            logger.info(f"Parsed progress: task_id={progress.task_id}, status={progress.status}, processed={progress.processed_files}/{progress.total_files}")
            # Используем mode='json' для правильной сериализации enum в строку
            result = progress.model_dump(mode='json')
            logger.info(f"Sending to WebSocket: {result}")
            await task_ws_manager.send_to_task(progress.task_id, result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing update: {e}", exc_info=True)
            return

    await rabbitmq_client.consume_updates(handler)


@app.on_event("startup")
async def on_startup() -> None:
    await init_models()
    # Подключение к RabbitMQ с retry (30 попыток, каждые 10 секунд)
    await rabbitmq_client.connect(max_retries=30, retry_delay=10)
    app.state.analysis_consumer = asyncio.create_task(_updates_consumer())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    consumer_task: asyncio.Task | None = getattr(app.state, "analysis_consumer", None)
    if consumer_task:
        consumer_task.cancel()
        with contextlib.suppress(Exception):
            await consumer_task
    await rabbitmq_client.close()

@app.get("/")
async def root():
    return {"message": "BFF Service is running"}

@app.get("/health")
async def health():
    """Проверка здоровья сервиса и зависимостей"""
    from app.services.yolov8_service import YOLOv8Service
    yolov8_service = YOLOv8Service()

    try:
        yolov8_status = await yolov8_service.health_check()

        return {
            "status": "healthy",
            "service": "bff-service",
            "dependencies": {
                "yolov8-model-service": yolov8_status
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "bff-service"
        }

