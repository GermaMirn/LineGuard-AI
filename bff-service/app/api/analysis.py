import io
import os
import zipfile
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.db import get_db_session
from app.models import AnalysisStatus
from app.schemas.analysis import AnalysisTaskCreateResponse, AnalysisTaskListItem, AnalysisTaskResponse
from app.services import analysis_tasks as analysis_tasks_service
from app.services.files_service import FilesService
from app.services.queue import rabbitmq_client
from app.services.websocket_manager import task_ws_manager

router = APIRouter()

settings = get_settings()
files_service = FilesService()

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".dng",
    ".raw",
    ".nef",
    ".cr2",
    ".arw",
}

RAW_EXTENSIONS = {".dng", ".raw", ".nef", ".cr2", ".arw"}


async def _ensure_size(upload_file) -> int:
    file_obj = upload_file.file
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)
    return size


@router.post(
    "/predict/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalysisTaskCreateResponse,
)
async def create_batch_task(
    files: List[UploadFile] = File(..., description="Список изображений"),
    conf: float = Query(0.35, ge=0.0, le=1.0, description="Порог уверенности"),
    route_name: Optional[str] = Query(None, max_length=250, description="Название маршрута"),
    preview_limit: int = Query(
        default=settings.PREVIEW_LIMIT,
        ge=1,
        le=settings.PREVIEW_LIMIT,
        description="Количество превью для истории",
    ),
    session: AsyncSession = Depends(get_db_session),
):
    if not files:
        raise HTTPException(status_code=400, detail="Не переданы файлы для анализа")

    if len(files) > settings.MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Максимальное количество файлов в батче: {settings.MAX_BATCH_FILES}",
        )

    total_bytes = 0
    file_descriptors = []
    for upload in files:
        extension = Path(upload.filename or "").suffix.lower()
        if extension in {".zip", ".tar"}:
            raise HTTPException(
                status_code=400,
                detail="ZIP/TAR архивы не поддерживаются. Загружайте отдельные изображения.",
            )

        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Формат {extension or 'unknown'} не поддерживается. "
                       f"Разрешены: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        size = await _ensure_size(upload)
        total_bytes += size
        file_descriptors.append((upload, extension, size))

    if total_bytes > settings.MAX_BATCH_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Суммарный размер файлов не должен превышать 10 ГБ",
        )

    task = await analysis_tasks_service.create_task(
        session,
        total_files=len(file_descriptors),
        total_bytes=total_bytes,
        confidence_threshold=conf,
        preview_limit=min(preview_limit, settings.PREVIEW_LIMIT),
        route_name=route_name,
    )

    # Оптимизация: сохраняем только первые N файлов как превью, остальные передаём в worker
    preview_limit_upload = settings.UPLOAD_PREVIEW_LIMIT
    stored_images = []
    archive_zip = io.BytesIO()

    # Разделяем файлы на preview и архивные
    preview_files = []
    archive_files = []

    for idx, (upload, extension, size) in enumerate(file_descriptors):
        upload.file.seek(0)
        file_content = await upload.read()
        upload.file.seek(0)

        if idx < preview_limit_upload:
            preview_files.append(upload)
        else:
            archive_files.append((upload, extension, file_content, idx))

    # Batch-загрузка preview файлов (один запрос вместо N)
    if preview_files:
        try:
            batch_result = await files_service.batch_upload_files(
                files=preview_files,
                project_id=str(task.id),
                file_type="ANALYSIS_ORIGINAL",
                uploaded_by=None,
            )

            for uploaded_file in batch_result.get("files", []):
                stored_images.append(
                    {
                        "file_id": UUID(uploaded_file["id"]),
                        "file_name": uploaded_file["file_name"],
                        "file_size": uploaded_file["file_size"],
                    }
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to batch upload preview files: {str(e)}"
            )

    # Архивные файлы добавляем в ZIP
    with zipfile.ZipFile(archive_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for upload, extension, file_content, idx in archive_files:
            safe_name = Path(upload.filename or f"file_{idx}{extension}").name
            zip_file.writestr(safe_name, file_content)
            await upload.close()

    # Закрываем preview файлы
    for upload in preview_files:
        await upload.close()

    # Сохраняем временный архив только для передачи в worker (будет удалён после обработки)
    archive_zip.seek(0)
    archive_data = archive_zip.getvalue() if archive_zip.getvalue() else None

    # Сохраняем временный архив в files-service (worker скачает, обработает и удалит)
    if archive_data and len(archive_data) > 0:
        archive_upload = await files_service.upload_bytes(
            data=archive_data,
            filename=f"{task.id}_temp_uploaded_archive.zip",
            content_type="application/zip",
            project_id=str(task.id),
            file_type="ANALYSIS_ARCHIVE",  # Временный, будет удалён worker'ом
        )
        await analysis_tasks_service.set_task_archives(
            session,
            task.id,
            originals_archive_id=UUID(archive_upload["id"]),
        )

    await analysis_tasks_service.add_images(
        session,
        task_id=task.id,
        images=stored_images,
    )

    await rabbitmq_client.publish_task(
        {
            "task_id": str(task.id),
            "confidence_threshold": conf,
            "preview_limit": preview_limit,
        }
    )

    return AnalysisTaskCreateResponse(task_id=task.id, status=task.status)


@router.get("/analysis/tasks/{task_id}", response_model=AnalysisTaskResponse)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    task = await analysis_tasks_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    previews = [
        image
        for image in task.images
        if image.is_preview
    ]

    return AnalysisTaskResponse(
        id=task.id,
        status=task.status,
        route_name=task.route_name,
        total_files=task.total_files,
        total_bytes=task.total_bytes,
        processed_files=task.processed_files,
        failed_files=task.failed_files,
        defects_found=task.defects_found,
        confidence_threshold=task.confidence_threshold,
        preview_limit=task.preview_limit,
        message=task.message,
        originals_archive_file_id=task.originals_archive_file_id,
        results_archive_file_id=task.results_archive_file_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        metadata=task.task_metadata,
        preview_files=[
            {
                "id": image.id,
                "file_id": image.file_id,
                "file_name": image.file_name,
                "file_size": image.file_size,
                "status": image.status,
                "is_preview": image.is_preview,
                "summary": image.summary,
                "result_file_id": image.result_file_id,
                "error_message": image.error_message,
            }
            for image in previews
        ],
    )


@router.get("/analysis/history", response_model=List[AnalysisTaskListItem])
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    tasks = await analysis_tasks_service.list_tasks(session, limit=limit)
    return [
        AnalysisTaskListItem(
            id=task.id,
            status=task.status,
            route_name=task.route_name,
            total_files=task.total_files,
            processed_files=task.processed_files,
            defects_found=task.defects_found,
            created_at=task.created_at,
            completed_at=task.completed_at,
        )
        for task in tasks
    ]


@router.get("/analysis/tasks/{task_id}/images")
async def get_task_images(
    task_id: UUID,
    skip: int = Query(0, ge=0, description="Количество пропущенных записей"),
    limit: int = Query(100, ge=1, le=500, description="Количество записей на странице"),
    include_thumbnails: bool = Query(False, description="Включить thumbnails в base64 (оптимизация)"),
    session: AsyncSession = Depends(get_db_session),
):
    """Получить все изображения задачи с пагинацией и URL для просмотра"""
    task = await analysis_tasks_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    images, total = await analysis_tasks_service.get_task_images(session, task_id, skip=skip, limit=limit)

    # Логируем для отладки - проверяем наличие summary с detections
    import logging
    logger = logging.getLogger(__name__)
    for img in images:
        if img.summary and img.summary.get("detections"):
            detections = img.summary.get("detections", [])
            manual_count = len([d for d in detections if d.get("is_manual")])
            if manual_count > 0:
                logger.info(f"📤 Returning image {img.id} with {len(detections)} detections ({manual_count} manual)")
                logger.info(f"📋 Manual detections details: {[d.get('class_ru', d.get('class', 'unknown')) for d in detections if d.get('is_manual')]}")

    # Если запрошены thumbnails, загружаем их batch'ом
    thumbnails_data = {}
    if include_thumbnails and images:
        try:
            # Собираем все file_id для batch download (только result файлы для превью)
            file_ids_to_fetch = []
            for image in images:
                # Для thumbnail используем result (с аннотациями), если есть, иначе original
                file_id = str(image.result_file_id if image.result_file_id else image.file_id)
                file_ids_to_fetch.append(file_id)

            # Batch download всех файлов за один запрос
            if file_ids_to_fetch:
                batch_result = await files_service.batch_download_files(file_ids_to_fetch)

                # Конвертируем в base64 для thumbnails (маленькие превью)
                from PIL import Image
                import io
                import base64

                for file_data in batch_result.get("files", []):
                    try:
                        # Создаем thumbnail (resize для уменьшения размера payload)
                        img = Image.open(io.BytesIO(file_data["content"]))

                        # Resize до 400px по ширине для thumbnail
                        max_width = 400
                        if img.width > max_width:
                            ratio = max_width / img.width
                            new_size = (max_width, int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)

                        # Конвертируем в JPEG и base64
                        buffer = io.BytesIO()
                        img.convert('RGB').save(buffer, format='JPEG', quality=85, optimize=True)
                        thumbnail_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

                        thumbnails_data[file_data["file_id"]] = f"data:image/jpeg;base64,{thumbnail_base64}"
                    except Exception as e:
                        # Если не удалось создать thumbnail, пропускаем
                        pass
        except Exception as e:
            # Если batch download не удался, просто не добавляем thumbnails
            pass

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "images": [
            {
                "id": image.id,
                "file_id": image.file_id,
                "file_name": image.file_name,
                "file_size": image.file_size,
                "status": image.status,
                "is_preview": image.is_preview,
                "summary": image.summary,
                "result_file_id": image.result_file_id,
                "error_message": image.error_message,
                "created_at": image.created_at,
                # URL для просмотра оригинального изображения
                "original_url": f"/api/files/{image.file_id}/view",
                # URL для просмотра результата с аннотациями (если есть)
                "result_url": f"/api/files/{image.result_file_id}/view" if image.result_file_id else None,
                # Thumbnail в base64 (если запрошено)
                "thumbnail": thumbnails_data.get(
                    str(image.result_file_id if image.result_file_id else image.file_id)
                ) if include_thumbnails else None,
            }
            for image in images
        ],
    }


@router.delete("/analysis/tasks/{task_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_image(
    task_id: UUID,
    image_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Удалить изображение из задачи"""
    # Проверяем существование задачи
    task = await analysis_tasks_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Удаляем изображение
    deleted_image_data = await analysis_tasks_service.delete_image(session, task_id, image_id)
    if not deleted_image_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    # Коммитим транзакцию
    await session.commit()

    # Удаляем файлы из files-service
    try:
        file_ids_to_delete = deleted_image_data.get('file_ids_to_delete', [])
        for file_id in file_ids_to_delete:
            try:
                await files_service.delete_file(str(file_id))
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                print(f"Failed to delete file {file_id}: {e}")
    except Exception as e:
        print(f"Error deleting files: {e}")

    return None


@router.delete("/analysis/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Удалить задачу и все её изображения"""
    # Проверяем существование задачи
    task = await analysis_tasks_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Удаляем задачу и получаем список файлов для удаления
    deleted_task_data = await analysis_tasks_service.delete_task(session, task_id)
    if not deleted_task_data:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Коммитим транзакцию
    await session.commit()

    # Удаляем файлы из files-service
    try:
        file_ids_to_delete = deleted_task_data.get('file_ids_to_delete', [])
        for file_id in file_ids_to_delete:
            try:
                await files_service.delete_file(str(file_id))
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                print(f"Failed to delete file {file_id}: {e}")
    except Exception as e:
        print(f"Error deleting files: {e}")

    return None


@router.websocket("/ws/tasks/{task_id}")
async def task_updates(task_id: str, websocket: WebSocket):
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await task_ws_manager.connect(task_uuid, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        task_ws_manager.disconnect(task_uuid, websocket)


@router.websocket("/ws/history")
async def history_updates(websocket: WebSocket):
    """
    WebSocket endpoint для получения обновлений всех задач в истории.
    Клиент получает обновления о статусе любой задачи в реальном времени.
    """
    await task_ws_manager.connect_history(websocket)
    try:
        while True:
            # Просто держим соединение открытым
            # Клиент может отправлять ping, но мы их игнорируем
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        task_ws_manager.disconnect_history(websocket)


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    name: Optional[str] = None
    is_defect: Optional[bool] = True  # По умолчанию повреждение


class AnnotationRequest(BaseModel):
    file_id: str
    bboxes: List[BBox]
    project_id: str
    file_type: str = "ANALYSIS_RESULT"


class ImageMetric(BaseModel):
    """Метрика для одного объекта на изображении"""
    detection_id: Optional[str] = None  # ID детекции, если привязана к ней
    class_name: str  # Название класса объекта
    class_name_ru: Optional[str] = None  # Название класса на русском
    confidence: float  # Уверенность модели (0-1)
    bbox: List[float]  # Координаты bbox [x1, y1, x2, y2]
    defect_type: Optional[str] = None  # Тип дефекта: "damage", "missing", "normal"
    severity: Optional[str] = None  # Серьезность: "high", "medium", "low", "none"
    description: Optional[str] = None  # Описание дефекта
    is_manual: bool = False  # Ручная аннотация


class ImageMetricsRequest(BaseModel):
    """Запрос на сохранение метрик изображения"""
    metrics: List[ImageMetric]  # Список метрик
    total_objects: Optional[int] = None  # Общее количество объектов
    defects_count: Optional[int] = None  # Количество дефектов
    has_defects: Optional[bool] = None  # Есть ли дефекты
    statistics: Optional[dict] = None  # Статистика по классам


@router.post("/analysis/tasks/{task_id}/images/{image_id}/annotate")
async def annotate_image(
    task_id: UUID,
    image_id: UUID,
    request: AnnotationRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Добавить аннотации (bbox) на изображение через annotation-service

    - **task_id**: ID задачи
    - **image_id**: ID изображения
    - **request**: Данные аннотации (bboxes, project_id, file_type)
    """
    try:
        # Проверяем, что задача существует
        task = await analysis_tasks_service.get_task(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что изображение существует и принадлежит задаче
        image = await analysis_tasks_service.get_image(db, image_id, task_id=task_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found or does not belong to this task"
            )

        # Используем file_id из изображения (result_file_id если есть, иначе file_id)
        file_id_to_annotate = str(image.result_file_id) if image.result_file_id else str(image.file_id)

        # Формируем запрос к annotation-service
        annotation_request = {
            "file_id": file_id_to_annotate,
            "bboxes": [bbox.dict() for bbox in request.bboxes],
            "project_id": request.project_id or str(task_id),
            "file_type": request.file_type or "ANALYSIS_RESULT"
        }

        # Проксируем запрос к annotation-service
        annotation_service_url = settings.ANNOTATION_SERVICE_URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{annotation_service_url}/annotations/annotate",
                json=annotation_request
            )

            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )

            result = response.json()

            # Обновляем result_file_id в базе данных новым file_id из результата
            # annotation-service возвращает "file_id" в ответе
            new_file_id = result.get("file_id")
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Annotate result: file_id={new_file_id}, image_id={image_id}")

            if new_file_id:
                try:
                    # Получаем текущий summary или создаем новый
                    current_summary = image.summary or {}

                    # Получаем существующие детекции или создаем пустой список
                    existing_detections = current_summary.get("detections", [])

                    # Сохраняем аннотации с названиями в summary
                    annotations = []
                    manual_detections = []

                    for bbox in request.bboxes:
                        annotation = {
                            "x": bbox.x,
                            "y": bbox.y,
                            "width": bbox.width,
                            "height": bbox.height,
                        }
                        if bbox.name:
                            annotation["name"] = bbox.name
                        annotation["is_defect"] = bbox.is_defect if bbox.is_defect is not None else True
                        annotations.append(annotation)

                        # Преобразуем ручную аннотацию в формат детекции
                        is_defect = bbox.is_defect if bbox.is_defect is not None else True
                        # Формат bbox: [x1, y1, x2, y2] (абсолютные координаты)
                        x1, y1 = bbox.x, bbox.y
                        x2, y2 = bbox.x + bbox.width, bbox.y + bbox.height
                        bbox_area = bbox.width * bbox.height

                        manual_detection = {
                            "class": bbox.name or "Ручная аннотация",
                            "class_ru": bbox.name or "Ручная аннотация",
                            "confidence": 1.0,  # 100% уверенность для ручных аннотаций
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "bbox_size": {
                                "width": bbox.width,
                                "height": bbox.height,
                                "area": bbox_area,
                                "is_small": bbox.width < 30 or bbox.height < 30
                            },
                            "defect_summary": {
                                "type": "Повреждение" if is_defect else "Норма",
                                "severity": "high" if is_defect else "none",
                                "description": "Ручная аннотация"
                            },
                            "is_manual": True  # Метка что это ручная аннотация
                        }
                        manual_detections.append(manual_detection)

                    # Объединяем существующие детекции с ручными
                    # Удаляем старые ручные детекции (с is_manual=True) и добавляем новые
                    # ВАЖНО: request.bboxes должен содержать ВСЕ маски (старые + новые), так как фронтенд загружает существующие
                    filtered_detections = [d for d in existing_detections if not d.get("is_manual", False)]
                    all_detections = filtered_detections + manual_detections

                    # Логируем для отладки
                    logger.info(f"📦 Request bboxes count: {len(request.bboxes)}")
                    logger.info(f"🔄 Existing detections: {len(existing_detections)} (manual: {len([d for d in existing_detections if d.get('is_manual')])})")
                    logger.info(f"✨ New manual detections: {len(manual_detections)}")
                    logger.info(f"📊 Total detections after merge: {len(all_detections)} (manual: {len(manual_detections)})")

                    # Обновляем счетчики
                    total_objects = len(all_detections)
                    defects_count = sum(1 for d in all_detections if (
                        d.get("defect_summary", {}).get("type") != "Норма" and
                        d.get("defect_summary", {}).get("severity") not in ["none", None]
                    ))

                    # Обновляем summary - ВАЖНО: создаем новый словарь для принудительного обновления
                    current_summary = {
                        **current_summary,  # Сохраняем существующие данные
                        "detections": all_detections,  # Обновляем детекции (включая ручные)
                        "manual_annotations": annotations,  # Сохраняем для обратной совместимости
                        "has_manual_annotations": len(annotations) > 0,
                        "total_objects": total_objects,
                        "defects_count": defects_count,
                        "has_defects": defects_count > 0
                    }

                    # Логируем для отладки
                    logger.info(f"🔄 Updating image {image_id} summary: total_objects={total_objects}, defects_count={defects_count}, manual_detections={len(manual_detections)}")
                    logger.info(f"📊 Summary detections count: {len(all_detections)}, manual: {len(manual_detections)}")
                    logger.info(f"📝 Manual detections: {[d.get('class_ru', d.get('class', 'unknown')) for d in manual_detections]}")
                    logger.info(f"💾 Saving summary with {len(all_detections)} detections to DB")
                    logger.info(f"🔍 Sample detection: {manual_detections[0] if manual_detections else 'None'}")

                    # ВАЖНО: Создаем новый объект summary для принудительного обновления JSON поля
                    import copy
                    summary_to_save = copy.deepcopy(current_summary)

                    await analysis_tasks_service.update_image(
                        db,
                        image_id,
                        result_file_id=UUID(new_file_id),
                        summary=summary_to_save
                    )
                    await db.commit()
                    logger.info(f"✅ Summary saved to DB for image {image_id}")

                    # Проверяем, что данные сохранились
                    updated_image = await analysis_tasks_service.get_image(db, image_id)
                    if updated_image and updated_image.summary:
                        saved_detections = updated_image.summary.get("detections", [])
                        saved_manual = [d for d in saved_detections if d.get("is_manual")]
                        logger.info(f"✅ Verified saved: {len(saved_detections)} detections, {len(saved_manual)} manual")
                    else:
                        logger.warning(f"⚠️ Image {image_id} summary is None after save")
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    logger.error(f"❌ Failed to update image result_file_id: {str(e)}", exc_info=True)
            else:
                logger.warning(f"⚠️ No file_id in annotation result for image {image_id}")

            return result

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to annotation service: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to annotate image: {str(e)}"
        )


@router.post("/analysis/tasks/{task_id}/images/{image_id}/metrics")
async def save_image_metrics(
    task_id: UUID,
    image_id: UUID,
    request: ImageMetricsRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Сохранить метрики для изображения

    - **task_id**: ID задачи
    - **image_id**: ID изображения
    - **request**: Данные метрик (metrics, total_objects, defects_count, etc.)
    """
    try:
        # Проверяем, что задача существует
        task = await analysis_tasks_service.get_task(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что изображение существует и принадлежит задаче
        image = await analysis_tasks_service.get_image(db, image_id, task_id=task_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found or does not belong to this task"
            )

        # Преобразуем метрики в формат детекций для совместимости
        detections = []
        for metric in request.metrics:
            detection = {
                "class": metric.class_name,
                "class_ru": metric.class_name_ru or metric.class_name,
                "confidence": metric.confidence,
                "bbox": metric.bbox,
                "bbox_size": {
                    "width": int(metric.bbox[2] - metric.bbox[0]) if len(metric.bbox) >= 4 else 0,
                    "height": int(metric.bbox[3] - metric.bbox[1]) if len(metric.bbox) >= 4 else 0,
                    "area": int((metric.bbox[2] - metric.bbox[0]) * (metric.bbox[3] - metric.bbox[1])) if len(metric.bbox) >= 4 else 0,
                    "is_small": False
                },
                "defect_summary": {
                    "type": "Повреждение" if metric.defect_type in ["damage", "missing"] else "Норма",
                    "severity": metric.severity or ("high" if metric.defect_type in ["damage", "missing"] else "none"),
                    "description": metric.description or ""
                },
                "is_manual": metric.is_manual
            }
            if metric.detection_id:
                detection["detection_id"] = metric.detection_id
            detections.append(detection)

        # Получаем текущий summary или создаем новый
        current_summary = image.summary or {}

        # Обновляем summary с новыми метриками
        updated_summary = {
            **current_summary,
            "detections": detections,
            "total_objects": request.total_objects or len(detections),
            "defects_count": request.defects_count or sum(1 for m in request.metrics if m.defect_type in ["damage", "missing"]),
            "has_defects": request.has_defects if request.has_defects is not None else (request.defects_count or 0) > 0,
            "statistics": request.statistics or current_summary.get("statistics", {})
        }

        # Сохраняем обновленный summary
        await analysis_tasks_service.update_image(
            db,
            image_id,
            summary=updated_summary
        )
        await db.commit()

        return {
            "image_id": str(image_id),
            "metrics_count": len(detections),
            "total_objects": updated_summary["total_objects"],
            "defects_count": updated_summary["defects_count"],
            "has_defects": updated_summary["has_defects"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save metrics: {str(e)}"
        )


@router.get("/analysis/tasks/{task_id}/images/{image_id}/metrics")
async def get_image_metrics(
    task_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить метрики для изображения

    - **task_id**: ID задачи
    - **image_id**: ID изображения
    """
    try:
        # Проверяем, что задача существует
        task = await analysis_tasks_service.get_task(db, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Проверяем, что изображение существует и принадлежит задаче
        image = await analysis_tasks_service.get_image(db, image_id, task_id=task_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found or does not belong to this task"
            )

        # Извлекаем метрики из summary
        summary = image.summary or {}
        detections = summary.get("detections", [])

        # Преобразуем детекции в формат метрик
        metrics = []
        for detection in detections:
            defect_summary = detection.get("defect_summary", {})
            defect_type = None
            if defect_summary.get("type") != "Норма":
                defect_type = "damage" if "повреж" in defect_summary.get("type", "").lower() else "missing"
            else:
                defect_type = "normal"

            metric = ImageMetric(
                detection_id=detection.get("detection_id"),
                class_name=detection.get("class", ""),
                class_name_ru=detection.get("class_ru", detection.get("class", "")),
                confidence=detection.get("confidence", 0.0),
                bbox=detection.get("bbox", []),
                defect_type=defect_type,
                severity=defect_summary.get("severity"),
                description=defect_summary.get("description"),
                is_manual=detection.get("is_manual", False)
            )
            metrics.append(metric)

        return {
            "image_id": str(image_id),
            "metrics": [m.dict() for m in metrics],
            "total_objects": summary.get("total_objects", len(metrics)),
            "defects_count": summary.get("defects_count", 0),
            "has_defects": summary.get("has_defects", False),
            "statistics": summary.get("statistics", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )

