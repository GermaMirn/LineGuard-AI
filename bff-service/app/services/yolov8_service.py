import httpx
from typing import Dict, Any
from fastapi import HTTPException, status, UploadFile
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class YOLOv8Service:
    def __init__(self):
        self.yolov8_service_url = settings.YOLOV8_SERVICE_URL
        self.timeout = 60.0

    async def predict_bytes(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        conf: float = 0.25,
    ) -> Dict[str, Any]:
        """Отправить байтовый буфер в YOLOv8 сервис."""
        try:
            if not content_type.startswith("image/"):
                logger.warning("Контент без image/*, продолжаем по расширению")

            max_bytes = settings.MAX_YOLO_FILE_SIZE_MB * 1024 * 1024
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Размер файла не должен превышать {settings.MAX_YOLO_FILE_SIZE_MB}MB",
                )

            logger.info(
                "Отправка запроса в YOLOv8: %s, размер: %s bytes, conf=%s",
                filename,
                len(content),
                conf,
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                files = {"file": (filename, content, content_type)}
                params = {"conf": conf} if conf != 0.25 else {}
                response = await client.post(
                    f"{self.yolov8_service_url}/predict",
                    files=files,
                    params=params,
                )

                if response.status_code != 200:
                    logger.error(
                        "Ошибка от YOLOv8 сервиса: %s - %s",
                        response.status_code,
                        response.text,
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Ошибка от YOLOv8 сервиса: {response.text}",
                    )

                result = response.json()
                logger.info(
                    "Детекция завершена: найдено %s объектов",
                    result.get("total_objects", 0),
                )
                return result

        except httpx.TimeoutException:
            logger.error("Таймаут при обращении к YOLOv8 сервису")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Таймаут при обращении к YOLOv8 сервису. Попробуйте позже.",
            )
        except httpx.ConnectError:
            logger.error("Не удалось подключиться к YOLOv8 сервису: %s", self.yolov8_service_url)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="YOLOv8 сервис недоступен. Проверьте, что сервис запущен.",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Ошибка при обработке запроса: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при обработке запроса: {str(e)}",
            )

    async def predict(
        self,
        file: UploadFile,
        conf: float = 0.25,
    ) -> Dict[str, Any]:
        """Совместимая обертка для UploadFile."""
        content = await file.read()
        content_type = file.content_type or "application/octet-stream"
        return await self.predict_bytes(
            filename=file.filename or "image",
            content=content,
            content_type=content_type,
            conf=conf,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Проверить здоровье YOLOv8 сервиса"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.yolov8_service_url}/health")
                if response.status_code == 200:
                    return response.json()
                return {"status": "unhealthy"}
        except Exception as e:
            logger.error(f"Ошибка при проверке здоровья YOLOv8: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        """Получить информацию о модели из YOLOv8 сервиса"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.yolov8_service_url}/model/info")

                if response.status_code != 200:
                    logger.error(f"Ошибка от YOLOv8 сервиса: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Ошибка от YOLOv8 сервиса: {response.text}"
                    )

                result = response.json()
                logger.info(f"Информация о модели получена: {result.get('num_classes', 0)} классов")
                return result

        except httpx.TimeoutException:
            logger.error("Таймаут при обращении к YOLOv8 сервису")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Таймаут при обращении к YOLOv8 сервису. Попробуйте позже."
            )
        except httpx.ConnectError:
            logger.error(f"Не удалось подключиться к YOLOv8 сервису: {self.yolov8_service_url}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="YOLOv8 сервис недоступен. Проверьте, что сервис запущен."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка при получении информации о модели: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при получении информации о модели: {str(e)}"
            )

