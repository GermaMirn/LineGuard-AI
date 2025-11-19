import io
import os
import zipfile
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    )

    # Оптимизация: сохраняем только первые N файлов как превью, остальные передаём в worker
    preview_limit_upload = settings.UPLOAD_PREVIEW_LIMIT
    stored_images = []
    archive_zip = io.BytesIO()

    with zipfile.ZipFile(archive_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for idx, (upload, extension, size) in enumerate(file_descriptors):
            upload.file.seek(0)
            file_content = await upload.read()
            upload.file.seek(0)

            # Первые N файлов сохраняем как превью
            if idx < preview_limit_upload:
                result = await files_service.upload_file(
                    file=upload,
                    project_id=str(task.id),
                    file_type="ANALYSIS_ORIGINAL",
                    uploaded_by=None,
                )
                stored_images.append(
                    {
                        "file_id": UUID(result["id"]),
                        "file_name": result["file_name"],
                        "file_size": result["file_size"],
                    }
                )
            else:
                # Остальные сразу в ZIP (временный, не сохраняем в files-service)
                safe_name = Path(upload.filename or f"file_{idx}{extension}").name
                zip_file.writestr(safe_name, file_content)

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
    session: AsyncSession = Depends(get_db_session),
):
    """Получить все изображения задачи с пагинацией и URL для просмотра"""
    task = await analysis_tasks_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    images, total = await analysis_tasks_service.get_task_images(session, task_id, skip=skip, limit=limit)

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
            }
            for image in images
        ],
    }


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

