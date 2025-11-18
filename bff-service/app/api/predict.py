from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from app.services.yolov8_service import YOLOv8Service
from app.api.auth import get_current_user
from app.core.config import get_settings

router = APIRouter()
yolov8_service = YOLOv8Service()
settings = get_settings()

@router.get("/model/info")
async def model_info(
    # current_user: dict = Depends(get_current_user)  # Можно включить для авторизации
):
    """
    Получить информацию о модели: метрики, классы, требования
    
    Проксирует запрос к YOLOv8 Model Service
    
    Returns:
        Информация о загруженной модели (метрики, классы, соответствие требованиям)
    """
    try:
        result = await yolov8_service.model_info()
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении информации о модели: {str(e)}"
        )

@router.post("/predict")
async def predict(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0, description="Порог уверенности для детекций"),
    # current_user: dict = Depends(get_current_user)  # Можно включить для авторизации
):
    """
    Детекция объектов на изображении
    
    Проксирует запрос к YOLOv8 Model Service
    
    Args:
        file: Загруженное изображение
        conf: Порог уверенности (0.0-1.0)
    """
    try:
        result = await yolov8_service.predict(file, conf)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )

