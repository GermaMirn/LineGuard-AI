from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, files, predict

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

