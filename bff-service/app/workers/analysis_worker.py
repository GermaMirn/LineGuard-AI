import asyncio
import io
import json
import logging
import mimetypes
import tempfile
import zipfile
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType, Message
from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.db import get_session
from app.db.session import init_models
from app.models import AnalysisStatus
from app.schemas.analysis import AnalysisTaskProgress
from app.services import analysis_tasks as analysis_tasks_service
from app.services.files_service import FilesService
from app.services.yolov8_service import YOLOv8Service

logger = logging.getLogger("analysis-worker")
logging.basicConfig(level=logging.INFO)

settings = get_settings()
files_service = FilesService()
yolo_service = YOLOv8Service()


async def publish_update(exchange, payload: Dict[str, Any]) -> None:
    progress = AnalysisTaskProgress(**payload)
    # Используем mode='json' для автоматической конвертации UUID в строки
    body = progress.model_dump_json().encode("utf-8")
    # Используем числовое значение: 1 = non-persistent, 2 = persistent
    await exchange.publish(
        Message(body, delivery_mode=1),
        routing_key="",
    )


async def update_task_status(task_id: UUID, **kwargs) -> None:
    async with get_session() as session:
        await analysis_tasks_service.update_task_progress(session, task_id, **kwargs)


async def update_image(image_id: UUID, **kwargs) -> None:
    async with get_session() as session:
        await analysis_tasks_service.update_image(session, image_id, **kwargs)


async def fetch_task_images(task_id: UUID, skip: int = 0, limit: int = 100) -> tuple[List[Dict[str, Any]], int]:
    async with get_session() as session:
        images, total = await analysis_tasks_service.get_task_images(session, task_id, skip=skip, limit=limit)
        return [
            {
                "id": image.id,
                "file_id": image.file_id,
                "file_name": image.file_name,
                "file_size": image.file_size,
            }
            for image in images
        ], total


def _get_font(size: int = 16):
    """Получить шрифт с поддержкой кириллицы"""
    try:
        # Пробуем загрузить стандартные шрифты Linux с поддержкой кириллицы
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
        ]

        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, size)
                logger.debug(f"Loaded font: {font_path}")
                return font
            except (OSError, IOError):
                continue

        # Если не нашли, используем встроенный шрифт (может не поддерживать кириллицу)
        try:
            return ImageFont.load_default()
        except:
            logger.warning("Could not load any font, text may not display correctly")
            return None
    except Exception as e:
        logger.warning(f"Error loading font: {e}")
        return None


def draw_annotations(image_bytes: bytes, detections: List[dict]) -> bytes:
    # Открываем изображение
    image = Image.open(io.BytesIO(image_bytes))

    # Конвертируем в RGB для правильного сохранения
    # Если изображение имеет альфа-канал или другой формат, конвертируем правильно
    if image.mode in ("RGBA", "LA", "P"):
        # Создаем белый фон для изображений с прозрачностью
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            rgb_image.paste(image, mask=image.split()[3])  # Используем альфа-канал как маску
        elif image.mode == "P":
            # Для палитровых изображений сначала конвертируем в RGBA
            if "transparency" in image.info:
                image = image.convert("RGBA")
                rgb_image.paste(image, mask=image.split()[3])
            else:
                rgb_image.paste(image.convert("RGB"))
        else:
            rgb_image.paste(image.convert("RGB"))
        image = rgb_image
    elif image.mode != "RGB":
        # Для других форматов просто конвертируем в RGB
        image = image.convert("RGB")

    # Загружаем шрифт с поддержкой кириллицы
    font = _get_font(16)

    # Создаем временное RGBA изображение для рисования с прозрачностью
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for detection in detections:
        bbox = detection.get("bbox", [])
        if len(bbox) != 4:
            continue
        x1, y1, x2, y2 = bbox
        x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
        label = detection.get("class_ru") or detection.get("class") or "object"
        conf = detection.get("confidence", 0) * 100
        # Определяем, является ли объект дефектом
        # Дефектные классы: bad_insulator, damaged_insulator
        class_name = detection.get("class", "")
        is_defect = class_name in ["bad_insulator", "damaged_insulator"]
        # Красный для дефектов, зеленый для обычных объектов
        color = (239, 68, 68, 255) if is_defect else (34, 197, 94, 255)

        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
        text = f"{label} {conf:.0f}%"

        # Используем шрифт для измерения текста, если доступен
        if font:
            try:
                # Используем textbbox для точного измерения с учетом шрифта
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_size = text_bbox[2] - text_bbox[0]
            except AttributeError:
                # Для старых версий PIL используем textlength
                try:
                    text_size = draw.textlength(text, font=font)
                except:
                    # Fallback на измерение без шрифта
                    text_size = draw.textlength(text) if hasattr(draw, 'textlength') else len(text) * 8
        else:
            # Без шрифта используем приблизительный размер
            text_size = draw.textlength(text) if hasattr(draw, 'textlength') else len(text) * 8

        draw.rectangle([(x1, max(0, y1 - 24)), (x1 + text_size + 10, y1)], fill=color)
        # Используем шрифт при рисовании текста
        if font:
            draw.text((x1 + 5, max(0, y1 - 20)), text, fill=(255, 255, 255, 255), font=font)
        else:
            draw.text((x1 + 5, max(0, y1 - 20)), text, fill=(255, 255, 255, 255))

    # Накладываем overlay на исходное изображение
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90, optimize=True)
    return output.getvalue()


async def process_task(payload: Dict[str, Any], exchange) -> None:
    task_id = UUID(payload["task_id"])
    conf = float(payload.get("confidence_threshold", 0.35))
    preview_limit = int(payload.get("preview_limit") or settings.PREVIEW_LIMIT)
    preview_limit = min(preview_limit, settings.PREVIEW_LIMIT)

    logger.info("Начало обработки задачи %s", task_id)
    await update_task_status(task_id, status=AnalysisStatus.PROCESSING, message="Обработка началась")

    # Получаем задачу для доступа к архиву
    async with get_session() as session:
        task = await analysis_tasks_service.get_task(session, task_id)
        if not task:
            await update_task_status(task_id, status=AnalysisStatus.FAILED, message="Задача не найдена")
            return

        preview_images, _ = await fetch_task_images(task_id, skip=0, limit=10)

        # Получаем архив с остальными файлами
        archive_images = []
        if task.originals_archive_file_id:
            logger.info("Распаковка архива с файлами от пользователя...")
            archive_bytes = await files_service.download_file(str(task.originals_archive_file_id))
            with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive_zip:
                for file_info in archive_zip.filelist:
                    if not file_info.is_dir():
                        archive_images.append({
                            "file_name": file_info.filename,
                            "file_size": file_info.file_size,
                            "data": archive_zip.read(file_info.filename),
                        })
            logger.info("Распаковано %d файлов из архива", len(archive_images))

    total_files = len(preview_images) + len(archive_images)
    if total_files == 0:
        await update_task_status(
            task_id,
            status=AnalysisStatus.FAILED,
            message="Нет файлов для обработки",
        )
        await publish_update(
            exchange,
            {
                "task_id": str(task_id),
                "status": AnalysisStatus.FAILED.value,
                "processed_files": 0,
                "total_files": 0,
                "failed_files": 0,
                "defects_found": 0,
                "message": "Нет файлов",
            },
        )
        return

    processed = 0
    failed = 0
    defects_found = 0
    stats = Counter()
    preview_queue_defect = deque()
    preview_queue_regular = deque()

    # Создаём только ZIP для результатов (входные файлы не сохраняем)
    tmp_results = tempfile.NamedTemporaryFile(delete=False, suffix="_results.zip")

    metadata = {
        "total_files": total_files,
        "total_objects": 0,
        "defects_found": 0,
        "class_stats": {},
    }

    try:
        # Используем ZIP_DEFLATED с поддержкой UTF-8 для имен файлов
        with zipfile.ZipFile(tmp_results.name, "w", compression=zipfile.ZIP_DEFLATED) as results_zip:
            # Создаем обе папки заранее (даже если они будут пустыми)
            damaged_folder = zipfile.ZipInfo("results/Поврежденные/")
            damaged_folder.flag_bits |= 0x800
            damaged_folder.compress_type = zipfile.ZIP_DEFLATED
            results_zip.writestr(damaged_folder, b"")

            normal_folder = zipfile.ZipInfo("results/Неповрежденные/")
            normal_folder.flag_bits |= 0x800
            normal_folder.compress_type = zipfile.ZIP_DEFLATED
            results_zip.writestr(normal_folder, b"")

            # Обрабатываем превью файлы (первые 10, уже в БД)
            # Оптимизация: скачиваем все preview файлы одним batch-запросом
            preview_files_data = {}
            if preview_images:
                try:
                    file_ids = [str(image["file_id"]) for image in preview_images]
                    batch_result = await files_service.batch_download_files(file_ids)

                    # Создаем словарь для быстрого поиска по file_id
                    for file_data in batch_result.get("files", []):
                        preview_files_data[file_data["file_id"]] = file_data["content"]

                    logger.info(f"Batch скачивание preview файлов: {len(preview_files_data)}/{len(file_ids)} успешно")
                except Exception as e:
                    logger.warning(f"Ошибка batch скачивания preview файлов: {e}. Используем fallback.")

            for image in preview_images:
                image_id = image["id"]
                safe_name = Path(image["file_name"]).name
                try:
                    await update_image(image_id, status=AnalysisStatus.PROCESSING)

                    # Используем данные из batch download или fallback на индивидуальное скачивание
                    file_id_str = str(image["file_id"])
                    if file_id_str in preview_files_data:
                        original_bytes = preview_files_data[file_id_str]
                    else:
                        logger.warning(f"Файл {file_id_str} не найден в batch, скачиваем отдельно")
                        original_bytes = await files_service.download_file(file_id_str)

                    mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
                    result = await yolo_service.predict_bytes(
                        filename=safe_name,
                        content=original_bytes,
                        content_type=mime_type,
                        conf=conf,
                    )

                    detections = result.get("detections", [])
                    annotated_bytes = draw_annotations(original_bytes, detections)
                    annotated_name = f"{Path(safe_name).stem}_annotated.jpg"

                    # Определяем папку в зависимости от наличия дефектов
                    has_defects = result.get("has_defects", False)
                    folder_name = "Поврежденные" if has_defects else "Неповрежденные"
                    zip_path = f"results/{folder_name}/{annotated_name}"

                    # Используем ZipInfo для правильной кодировки UTF-8
                    zip_info = zipfile.ZipInfo(zip_path)
                    # Устанавливаем флаг UTF-8 (0x800) для поддержки кириллицы в именах файлов
                    zip_info.flag_bits |= 0x800
                    zip_info.compress_type = zipfile.ZIP_DEFLATED
                    results_zip.writestr(zip_info, annotated_bytes)

                    metadata["total_objects"] += result.get("total_objects", 0)
                    metadata["defects_found"] += result.get("defects_count", 0)
                    stats.update(result.get("statistics") or {})
                    if result.get("has_defects"):
                        defects_found += result.get("defects_count", 0)

                    preview_candidate = {
                        "image_id": image_id,
                        "annotations": annotated_bytes,
                        "summary": result,
                        "file_name": annotated_name,
                    }

                    if result.get("has_defects"):
                        if len(preview_queue_defect) < preview_limit:
                            preview_queue_defect.append(preview_candidate)
                    elif len(preview_queue_regular) < preview_limit:
                        preview_queue_regular.append(preview_candidate)

                    await update_image(
                        image_id,
                        status=AnalysisStatus.COMPLETED,
                        summary=result,
                    )
                    processed += 1

                except Exception as exc:
                    logger.exception("Ошибка обработки превью изображения %s: %s", image_id, exc)
                    failed += 1
                    await update_image(
                        image_id,
                        status=AnalysisStatus.FAILED,
                        error_message=str(exc),
                    )

                # Обновляем статус каждые 100 файлов для производительности
                if processed % 100 == 0 or failed % 100 == 0:
                    await update_task_status(
                        task_id,
                        processed_files=processed,
                        failed_files=failed,
                        defects_found=defects_found,
                    )
                    await publish_update(
                        exchange,
                        {
                            "task_id": str(task_id),
                            "status": AnalysisStatus.PROCESSING.value,
                            "processed_files": processed,
                            "total_files": total_files,
                            "failed_files": failed,
                            "defects_found": defects_found,
                            "message": f"Обработано {processed}/{total_files} файлов",
                        },
                    )

            # Обрабатываем файлы из архива (остальные 49,990) - теперь сохраняем ВСЕ в БД
            # Оптимизация: загружаем файлы батчами по 100 штук
            BATCH_SIZE = 100
            for batch_start in range(0, len(archive_images), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(archive_images))
                current_batch = archive_images[batch_start:batch_end]

                # Подготавливаем batch данных для загрузки
                batch_upload_data = []
                for archive_file in current_batch:
                    safe_name = archive_file["file_name"]
                    original_bytes = archive_file["data"]
                    mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

                    batch_upload_data.append({
                        "data": original_bytes,
                        "filename": safe_name,
                        "content_type": mime_type,
                    })

                # Batch-загрузка файлов (один запрос вместо N)
                try:
                    batch_result = await files_service.batch_upload_bytes(
                        files_data=batch_upload_data,
                        project_id=str(task_id),
                        file_type="ANALYSIS_ORIGINAL",
                    )

                    uploaded_files = batch_result.get("files", [])

                    # Создаём записи в БД для всех загруженных файлов
                    async with get_session() as session:
                        image_records_data = []
                        for i, uploaded_file in enumerate(uploaded_files):
                            image_records_data.append({
                                "file_id": UUID(uploaded_file["id"]),
                                "file_name": uploaded_file["file_name"],
                                "file_size": uploaded_file["file_size"],
                            })

                        new_images = await analysis_tasks_service.add_images(
                            session,
                            task_id,
                            image_records_data
                        )

                    # Обрабатываем каждый файл из batch
                    for idx, archive_file in enumerate(current_batch):
                        if idx >= len(new_images):
                            logger.warning(f"Файл {archive_file['file_name']} не был добавлен в БД")
                            continue

                        image_id = new_images[idx].id
                        safe_name = archive_file["file_name"]
                        original_bytes = archive_file["data"]

                        try:
                            await update_image(image_id, status=AnalysisStatus.PROCESSING)

                            mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
                            result = await yolo_service.predict_bytes(
                                filename=safe_name,
                                content=original_bytes,
                                content_type=mime_type,
                                conf=conf,
                            )

                            detections = result.get("detections", [])
                            annotated_bytes = draw_annotations(original_bytes, detections)
                            annotated_name = f"{Path(safe_name).stem}_annotated.jpg"

                            # Определяем папку в зависимости от наличия дефектов
                            has_defects = result.get("has_defects", False)
                            folder_name = "Поврежденные" if has_defects else "Неповрежденные"
                            zip_path = f"results/{folder_name}/{annotated_name}"

                            # Используем ZipInfo для правильной кодировки UTF-8
                            zip_info = zipfile.ZipInfo(zip_path)
                            # Устанавливаем флаг UTF-8 (0x800) для поддержки кириллицы в именах файлов
                            zip_info.flag_bits |= 0x800
                            zip_info.compress_type = zipfile.ZIP_DEFLATED
                            results_zip.writestr(zip_info, annotated_bytes)

                            metadata["total_objects"] += result.get("total_objects", 0)
                            metadata["defects_found"] += result.get("defects_count", 0)
                            stats.update(result.get("statistics") or {})
                            if result.get("has_defects"):
                                defects_found += result.get("defects_count", 0)

                            # Сохраняем результат в БД
                            await update_image(
                                image_id,
                                status=AnalysisStatus.COMPLETED,
                                summary=result,
                            )

                            # Для превью
                            preview_candidate = {
                                "image_id": image_id,
                                "annotations": annotated_bytes,
                                "summary": result,
                                "file_name": annotated_name,
                            }

                            if result.get("has_defects"):
                                if len(preview_queue_defect) < preview_limit:
                                    preview_queue_defect.append(preview_candidate)
                            elif len(preview_queue_regular) < preview_limit:
                                preview_queue_regular.append(preview_candidate)

                            processed += 1

                        except Exception as exc:
                            logger.exception("Ошибка обработки файла из архива %s: %s", safe_name, exc)
                            failed += 1
                            await update_image(
                                image_id,
                                status=AnalysisStatus.FAILED,
                                error_message=str(exc),
                            )

                        # Обновляем статус каждые 100 файлов для производительности
                        if processed % 100 == 0 or failed % 100 == 0:
                            await update_task_status(
                                task_id,
                                processed_files=processed,
                                failed_files=failed,
                                defects_found=defects_found,
                            )
                            await publish_update(
                                exchange,
                                {
                                    "task_id": str(task_id),
                                    "status": AnalysisStatus.PROCESSING.value,
                                    "processed_files": processed,
                                    "total_files": total_files,
                                    "failed_files": failed,
                                    "defects_found": defects_found,
                                    "message": f"Обработано {processed}/{total_files} файлов",
                                },
                            )

                except Exception as batch_exc:
                    logger.exception("Ошибка batch-загрузки файлов: %s", batch_exc)
                    # Если batch-загрузка не удалась, отмечаем все файлы как failed
                    failed += len(current_batch)
                    continue

        # Вычисляем проценты по типам объектов
        total_objects_for_stats = metadata["total_objects"]
        class_stats_percent = {}
        if total_objects_for_stats > 0:
            for class_name, count in stats.items():
                class_stats_percent[class_name] = {
                    "count": count,
                    "percentage": round((count / total_objects_for_stats) * 100, 2)
                }

        metadata["class_stats"] = dict(stats)
        metadata["class_stats_percent"] = class_stats_percent

        # Выбираем лучшие превью (10 штук)
        previews_to_use: List[Dict[str, Any]] = list(preview_queue_defect)
        if len(previews_to_use) < preview_limit:
            previews_to_use.extend(list(preview_queue_regular)[: preview_limit - len(previews_to_use)])

        # Сохраняем превью (теперь все имеют image_id)
        for preview in previews_to_use:
            if preview["image_id"] is not None:
                upload = await files_service.upload_bytes(
                    data=preview["annotations"],
                    filename=preview["file_name"],
                    content_type="image/jpeg",
                    project_id=str(task_id),
                    file_type="ANALYSIS_PREVIEW",
                )
                await update_image(
                    preview["image_id"],
                    is_preview=True,
                    result_file_id=UUID(upload["id"]),
                    summary=preview["summary"],
                )

        # Удаляем временный входной архив (от пользователя) - он нам больше не нужен
        if task.originals_archive_file_id:
            try:
                logger.info("Удаление временного входного архива...")
                await files_service.delete_file(str(task.originals_archive_file_id))
            except Exception as e:
                logger.warning(f"Не удалось удалить временный архив: {e}")

        # Сохраняем только результаты от нейронки
        tmp_results.flush()
        with open(tmp_results.name, "rb") as res_file:
            results_data = res_file.read()

        results_upload = await files_service.upload_bytes(
            data=results_data,
            filename=f"{task_id}_results.zip",
            content_type="application/zip",
            project_id=str(task_id),
            file_type="ANALYSIS_ARCHIVE",
        )

        async with get_session() as session:
            await analysis_tasks_service.set_task_archives(
                session,
                task_id,
                originals_archive_id=None,  # Не сохраняем входной архив
                results_archive_id=UUID(results_upload["id"]),
                metadata=metadata,
            )

        final_status = AnalysisStatus.COMPLETED if failed == 0 else AnalysisStatus.FAILED
        await update_task_status(
            task_id,
            status=final_status,
            processed_files=processed,
            failed_files=failed,
            defects_found=defects_found,
            message="Завершено" if final_status == AnalysisStatus.COMPLETED else "Задача завершилась с ошибками",
        )
        await publish_update(
            exchange,
            {
                "task_id": str(task_id),
                "status": final_status.value,
                "processed_files": processed,
                "total_files": total_files,
                "failed_files": failed,
                "defects_found": defects_found,
                "message": "Задача завершена",
            },
        )

    finally:
        try:
            tmp_results.close()
        finally:
            Path(tmp_results.name).unlink(missing_ok=True)


async def worker() -> None:
    await init_models()

    # Подключение к RabbitMQ с retry (30 попыток, каждые 10 секунд)
    max_retries = 30
    retry_delay = 10
    connection = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Попытка подключения к RabbitMQ ({attempt}/{max_retries})...")
            connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            logger.info("✅ Успешно подключено к RabbitMQ")
            break
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"❌ Не удалось подключиться к RabbitMQ после {max_retries} попыток: {e}")
                raise
            logger.warning(f"⚠️ Ошибка подключения к RabbitMQ (попытка {attempt}/{max_retries}): {e}. Повтор через {retry_delay} сек...")
            await asyncio.sleep(retry_delay)

    if not connection:
        raise RuntimeError("Не удалось установить подключение к RabbitMQ")

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(settings.ANALYSIS_QUEUE_NAME, durable=True)
    exchange = await channel.declare_exchange(
        settings.ANALYSIS_UPDATES_EXCHANGE,
        ExchangeType.FANOUT,
        durable=True,
    )

    logger.info("Analysis worker запущен. Ожидание задач...")
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                except json.JSONDecodeError:
                    logger.error("Неверный формат сообщения")
                    continue

                try:
                    await process_task(payload, exchange)
                except Exception as exc:
                    logger.exception("Ошибка обработки задачи: %s", exc)


if __name__ == "__main__":
    asyncio.run(worker())

