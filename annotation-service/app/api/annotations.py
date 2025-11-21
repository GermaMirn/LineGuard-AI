from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel
from app.services.annotation_service import AnnotationService
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()
annotation_service = AnnotationService()


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class AnnotationRequest(BaseModel):
    file_id: str
    bboxes: List[BBox]
    project_id: str
    file_type: str = "ANALYSIS_RESULT"


@router.post("/annotate")
async def annotate_image(request: AnnotationRequest):
    """
    Добавить аннотации (bbox) на изображение и сохранить результат
    
    - **file_id**: ID исходного изображения в files-service
    - **bboxes**: Список координат bbox для рисования
    - **project_id**: ID проекта
    - **file_type**: Тип файла (по умолчанию "ANALYSIS_RESULT")
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if not request.bboxes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one bbox is required"
            )
        
        logger.info(f"Annotating image: file_id={request.file_id}, project_id={request.project_id}, bboxes_count={len(request.bboxes)}")
        
        # Обрабатываем аннотацию
        result = await annotation_service.annotate_image(
            file_id=request.file_id,
            bboxes=request.bboxes,
            project_id=request.project_id,
            file_type=request.file_type
        )
        
        logger.info(f"Image annotated successfully: new_file_id={result.get('id')}")
        
        return {
            "success": True,
            "file_id": result.get("id"),  # files-service возвращает "id"
            "filename": result.get("file_name"),  # files-service возвращает "file_name"
            "message": "Image annotated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to annotate image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to annotate image: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}

