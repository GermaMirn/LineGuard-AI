import httpx
import io
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from app.core.config import get_settings
from pydantic import BaseModel

settings = get_settings()


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    name: Optional[str] = None
    is_defect: Optional[bool] = True  # По умолчанию повреждение


class AnnotationService:
    def __init__(self):
        self.files_service_url = settings.FILES_SERVICE_URL
        self.timeout = 60.0  # Увеличенный таймаут для обработки изображений
        self.bbox_color = settings.BBOX_COLOR
        self.bbox_thickness = settings.BBOX_THICKNESS

    async def download_image(self, file_id: str) -> bytes:
        """Скачать изображение из files-service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.files_service_url}/files/{file_id}/download"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Image file not found"
                    )

                response.raise_for_status()
                return response.content

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )

    async def upload_annotated_image(
        self,
        image_data: bytes,
        filename: str,
        project_id: str,
        file_type: str
    ) -> Dict[str, Any]:
        """Загрузить аннотированное изображение обратно в files-service"""
        try:
            # Валидация project_id как UUID
            from uuid import UUID as UUIDType
            try:
                UUIDType(project_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid project_id format: {project_id}"
                )

            files = {
                "file": (filename, image_data, "image/jpeg")
            }
            data = {
                "project_id": project_id,
                "file_type": file_type,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.files_service_url}/files/upload",
                    files=files,
                    data=data
                )

                if response.status_code == 413:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds maximum allowed size"
                    )
                elif response.status_code == 400:
                    error_detail = "Bad request"
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("detail", str(error_json))
                    except:
                        error_detail = response.text
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Files service error: {error_detail}"
                    )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )

    def draw_bboxes_on_image(
        self,
        image_data: bytes,
        bboxes: List[BBox]
    ) -> bytes:
        """
        Нарисовать bbox на изображении

        Args:
            image_data: Байты исходного изображения
            bboxes: Список координат bbox

        Returns:
            Байты обработанного изображения
        """
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(image_data))

            # Конвертируем в RGB если нужно (для PNG с прозрачностью)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Создаем объект для рисования
            draw = ImageDraw.Draw(image)

            # Загружаем шрифт для текста (если доступен)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except:
                    font = ImageFont.load_default()

            # Рисуем каждый bbox
            for bbox in bboxes:
                # Координаты прямоугольника
                left = bbox.x
                top = bbox.y
                right = bbox.x + bbox.width
                bottom = bbox.y + bbox.height

                # Определяем цвет рамки в зависимости от типа объекта
                is_defect = bbox.is_defect if bbox.is_defect is not None else True
                bbox_color = (239, 68, 68) if is_defect else (16, 185, 129)  # Красный для дефекта, зеленый для нормы

                # Рисуем прямоугольник с нужной толщиной
                # Используем несколько прямоугольников для создания эффекта толщины
                for i in range(self.bbox_thickness):
                    offset = i - (self.bbox_thickness // 2)
                    draw.rectangle(
                        [left + offset, top + offset, right - offset, bottom - offset],
                        outline=bbox_color
                    )

                # Рисуем название маски, если есть
                if bbox.name:
                    # Определяем цвет в зависимости от типа
                    is_defect = bbox.is_defect if bbox.is_defect is not None else True
                    bg_color = (239, 68, 68) if is_defect else (16, 185, 129)  # Красный для дефекта, зеленый для нормы
                    
                    # Получаем размер текста
                    bbox_text = bbox.name
                    try:
                        bbox_text_bbox = draw.textbbox((0, 0), bbox_text, font=font)
                        text_width = bbox_text_bbox[2] - bbox_text_bbox[0]
                        text_height = bbox_text_bbox[3] - bbox_text_bbox[1]
                    except:
                        # Fallback если textbbox не доступен
                        text_width = len(bbox_text) * 8
                        text_height = 16

                    # Рисуем фон для текста
                    text_bg_left = left
                    text_bg_top = max(0, top - text_height - 4)
                    text_bg_right = left + text_width + 8
                    text_bg_bottom = top

                    # Рисуем непрозрачный фон для текста
                    draw.rectangle(
                        [text_bg_left, text_bg_top, text_bg_right, text_bg_bottom],
                        fill=bg_color
                    )

                    # Рисуем текст
                    draw.text(
                        (left + 4, text_bg_top + 2),
                        bbox_text,
                        fill=(255, 255, 255),  # Белый текст
                        font=font
                    )

            # Сохраняем изображение в байты
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            output.seek(0)

            return output.getvalue()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process image: {str(e)}"
            )

    async def annotate_image(
        self,
        file_id: str,
        bboxes: List[BBox],
        project_id: str,
        file_type: str = "ANALYSIS_RESULT"
    ) -> Dict[str, Any]:
        """
        Полный процесс аннотации изображения:
        1. Скачать исходное изображение
        2. Нарисовать bbox
        3. Сохранить результат обратно в files-service

        Args:
            file_id: ID исходного изображения
            bboxes: Список координат bbox
            project_id: ID проекта
            file_type: Тип файла для сохранения

        Returns:
            Информация о сохраненном файле
        """
        try:
            # 1. Скачиваем исходное изображение
            image_data = await self.download_image(file_id)

            # 2. Получаем метаданные файла для имени
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                metadata_response = await client.get(
                    f"{self.files_service_url}/files/{file_id}"
                )
                if metadata_response.status_code == 200:
                    metadata = metadata_response.json()
                    original_filename = metadata.get("filename", "annotated_image.jpg")
                    # Убеждаемся, что filename имеет расширение
                    if not original_filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # Если нет расширения, добавляем .jpg
                        if '.' not in original_filename:
                            original_filename = f"{original_filename}.jpg"
                    # Добавляем префикс к имени файла
                    filename = f"annotated_{original_filename}"
                else:
                    filename = "annotated_image.jpg"

            # 3. Рисуем bbox на изображении
            annotated_image_data = self.draw_bboxes_on_image(image_data, bboxes)

            # 4. Загружаем результат обратно в files-service
            result = await self.upload_annotated_image(
                image_data=annotated_image_data,
                filename=filename,
                project_id=project_id,
                file_type=file_type
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to annotate image: {str(e)}"
            )

