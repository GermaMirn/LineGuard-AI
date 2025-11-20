from datetime import datetime
from typing import Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisTask, AnalysisImage, AnalysisStatus


async def create_task(
    session: AsyncSession,
    *,
    total_files: int,
    total_bytes: int,
    confidence_threshold: float,
    preview_limit: int,
    route_name: Optional[str] = None,
) -> AnalysisTask:
    task = AnalysisTask(
        total_files=total_files,
        total_bytes=total_bytes,
        confidence_threshold=confidence_threshold,
        preview_limit=preview_limit,
        route_name=route_name,
        status=AnalysisStatus.QUEUED,
    )
    session.add(task)
    await session.flush()
    return task


async def add_images(
    session: AsyncSession,
    task_id: UUID,
    images: Iterable[dict],
) -> List[AnalysisImage]:
    image_models: List[AnalysisImage] = []
    for image in images:
        model = AnalysisImage(
            task_id=task_id,
            file_id=image["file_id"],
            file_name=image["file_name"],
            file_size=image["file_size"],
            status=AnalysisStatus.QUEUED,
        )
        session.add(model)
        image_models.append(model)
    await session.flush()
    return image_models


async def get_task(session: AsyncSession, task_id: UUID) -> Optional[AnalysisTask]:
    result = await session.execute(
        select(AnalysisTask).where(AnalysisTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_tasks(session: AsyncSession, limit: int = 20) -> List[AnalysisTask]:
    stmt = (
        select(AnalysisTask)
        .order_by(AnalysisTask.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def update_task_progress(
    session: AsyncSession,
    task_id: UUID,
    *,
    processed_files: Optional[int] = None,
    failed_files: Optional[int] = None,
    defects_found: Optional[int] = None,
    status: Optional[AnalysisStatus] = None,
    message: Optional[str] = None,
) -> Optional[AnalysisTask]:
    task = await get_task(session, task_id)
    if not task:
        return None

    if processed_files is not None:
        task.processed_files = processed_files
    if failed_files is not None:
        task.failed_files = failed_files
    if defects_found is not None:
        task.defects_found = defects_found
    if status is not None:
        task.status = status
        if status in {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}:
            task.completed_at = datetime.utcnow()
    if message is not None:
        task.message = message

    task.updated_at = datetime.utcnow()
    session.add(task)
    await session.flush()
    return task


async def get_task_images(
    session: AsyncSession,
    task_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[List[AnalysisImage], int]:
    """Получить изображения задачи с пагинацией"""
    # Общее количество
    count_stmt = select(func.count(AnalysisImage.id)).where(AnalysisImage.task_id == task_id)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Изображения с пагинацией
    stmt = (
        select(AnalysisImage)
        .where(AnalysisImage.task_id == task_id)
        .order_by(AnalysisImage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars()), total


async def update_image(
    session: AsyncSession,
    image_id: UUID,
    *,
    status: Optional[AnalysisStatus] = None,
    summary: Optional[dict] = None,
    is_preview: Optional[bool] = None,
    result_file_id: Optional[UUID] = None,
    error_message: Optional[str] = None,
) -> Optional[AnalysisImage]:
    stmt = select(AnalysisImage).where(AnalysisImage.id == image_id)
    result = await session.execute(stmt)
    image = result.scalar_one_or_none()
    if not image:
        return None

    if status is not None:
        image.status = status
    if summary is not None:
        image.summary = summary
    if is_preview is not None:
        image.is_preview = is_preview
    if result_file_id is not None:
        image.result_file_id = result_file_id
    if error_message is not None:
        image.error_message = error_message

    image.updated_at = datetime.utcnow()
    session.add(image)
    await session.flush()
    return image


async def set_task_archives(
    session: AsyncSession,
    task_id: UUID,
    *,
    originals_archive_id: Optional[UUID] = None,
    results_archive_id: Optional[UUID] = None,
    metadata: Optional[dict] = None,
) -> Optional[AnalysisTask]:
    task = await get_task(session, task_id)
    if not task:
        return None

    if originals_archive_id:
        task.originals_archive_file_id = originals_archive_id
    if results_archive_id:
        task.results_archive_file_id = results_archive_id
    if metadata is not None:
        task.task_metadata = metadata

    task.updated_at = datetime.utcnow()
    session.add(task)
    await session.flush()
    return task

