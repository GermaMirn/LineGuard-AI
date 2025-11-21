"""
API роутеры для YOLOv8 Model Service
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from PIL import Image
import io
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, List

from app.core.config import get_settings
from app.services.predictor import YOLOPredictor
from app.schemas.predict import PredictResponse, ModelInfoResponse, HealthResponse, BatchPredictResponse

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()

# Глобальный предиктор (ленивая загрузка)
predictor: Optional[YOLOPredictor] = None

def get_predictor() -> YOLOPredictor:
    """Ленивая загрузка модели"""
    global predictor
    if predictor is None:
        model_path = settings.MODEL_PATH
        if not os.path.exists(model_path):
            logger.error(f"Модель не найдена: {model_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Модель не найдена: {model_path}. Убедитесь, что модель загружена в /app/models/"
            )
        logger.info(f"Загрузка модели: {model_path}")
        predictor = YOLOPredictor(model_path, settings.DEFAULT_CONF_THRESHOLD)
        logger.info("✅ Модель успешно загружена")
    return predictor

@router.get("/health", response_model=HealthResponse)
async def health():
    """Проверка здоровья сервиса"""
    try:
        pred = get_predictor()
        return HealthResponse(
            status="healthy",
            model_loaded=pred is not None,
            service="yolov8-model-service"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            model_loaded=False,
            service="yolov8-model-service",
            error=str(e)
        )

@router.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    """
    Информация о модели: метрики, классы, требования

    Returns:
        Информация о загруженной модели
    """
    try:
        pred = get_predictor()
        model_path = settings.MODEL_PATH

        # Попытка получить метрики из файла results.yaml (если есть)
        metrics = {}
        try:
            import yaml
            import torch

            # Вариант 1: Попытка извлечь метрики из самого .pt файла
            try:
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                # YOLOv8 может хранить метрики в разных местах checkpoint
                if isinstance(checkpoint, dict):
                    # Логируем структуру для отладки
                    logger.debug(f"Checkpoint keys: {list(checkpoint.keys())[:10]}...")  # Первые 10 ключей

                    # Приоритет 1: best_fitness (это mAP50 для best.pt)
                    if 'best_fitness' in checkpoint:
                        best_fitness = checkpoint.get('best_fitness', 0.0)
                        logger.info(f"Найден best_fitness (mAP50): {best_fitness}")

                        # Пытаемся найти другие метрики
                        metrics_dict = checkpoint.get('metrics', {})
                        if isinstance(metrics_dict, dict):
                            metrics = {
                                "mAP50": best_fitness,
                                "mAP50-95": metrics_dict.get("metrics/mAP50-95(B)",
                                                              metrics_dict.get("mAP50-95",
                                                              metrics_dict.get("mAP50:0.5:0.95", 0.0))),
                                "precision": metrics_dict.get("metrics/precision(B)",
                                             metrics_dict.get("precision",
                                             metrics_dict.get("metrics/precision", 0.0))),
                                "recall": metrics_dict.get("metrics/recall(B)",
                                          metrics_dict.get("recall",
                                          metrics_dict.get("metrics/recall", 0.0)))
                            }
                        else:
                            # Если metrics не словарь, используем только best_fitness
                            metrics = {
                                "mAP50": best_fitness,
                                "mAP50-95": 0.0,
                                "precision": 0.0,
                                "recall": 0.0
                            }

                    # Приоритет 2: metrics напрямую
                    elif 'metrics' in checkpoint:
                        metrics_dict = checkpoint['metrics']
                        if isinstance(metrics_dict, dict):
                            metrics = {
                                "mAP50": metrics_dict.get("metrics/mAP50(B)",
                                             metrics_dict.get("mAP50",
                                             metrics_dict.get("mAP50:0.5", 0.0))),
                                "mAP50-95": metrics_dict.get("metrics/mAP50-95(B)",
                                             metrics_dict.get("mAP50-95",
                                             metrics_dict.get("mAP50:0.5:0.95", 0.0))),
                                "precision": metrics_dict.get("metrics/precision(B)",
                                             metrics_dict.get("precision",
                                             metrics_dict.get("metrics/precision", 0.0))),
                                "recall": metrics_dict.get("metrics/recall(B)",
                                          metrics_dict.get("recall",
                                          metrics_dict.get("metrics/recall", 0.0)))
                            }

                    # Приоритет 3: Проверяем все ключи на наличие метрик
                    if not metrics or not any(metrics.values()):
                        # Ищем любые ключи, содержащие метрики
                        for key, value in checkpoint.items():
                            if isinstance(value, (int, float)) and 0 <= value <= 1:
                                if 'map' in key.lower() or 'fitness' in key.lower():
                                    if 'mAP50' not in metrics or metrics['mAP50'] == 0.0:
                                        metrics['mAP50'] = float(value)
                                        logger.info(f"Найдена метрика в ключе {key}: {value}")
                                        break
            except Exception as pt_error:
                logger.warning(f"Не удалось извлечь метрики из .pt файла: {pt_error}")
                logger.debug(f"Детали ошибки: {str(pt_error)}", exc_info=True)

            # Вариант 2: Попытка получить метрики из файла results.yaml (если есть)
            if not any(metrics.values()):  # Если не нашли метрики в .pt
                possible_paths = [
                    os.path.join(os.path.dirname(model_path), "results.yaml"),
                    os.path.join(os.path.dirname(model_path), "args.yaml"),
                    os.path.join(os.path.dirname(os.path.dirname(model_path)), "results.yaml"),
                ]

                for results_path in possible_paths:
                    if os.path.exists(results_path):
                        with open(results_path, 'r', encoding='utf-8') as f:
                            results = yaml.safe_load(f)
                            if results:
                                # YOLOv8 может хранить метрики в разных форматах
                                metrics = {
                                    "mAP50": results.get("metrics/mAP50(B)", results.get("mAP50", 0.0)),
                                    "mAP50-95": results.get("metrics/mAP50-95(B)", results.get("mAP50-95", 0.0)),
                                    "precision": results.get("metrics/precision(B)", results.get("precision", 0.0)),
                                    "recall": results.get("metrics/recall(B)", results.get("recall", 0.0))
                                }
                                if any(metrics.values()):  # Если нашли хотя бы одну метрику
                                    break
        except ImportError:
            logger.warning("yaml не установлен, метрики недоступны")
        except Exception as e:
            logger.warning(f"Не удалось загрузить метрики: {e}")

        classes = list(pred.model.names.values()) if hasattr(pred.model, 'names') else []
        num_classes = len(pred.model.names) if hasattr(pred.model, 'names') else 0

        return ModelInfoResponse(
            model_path=model_path,
            model_exists=os.path.exists(model_path),
            classes=classes,
            num_classes=num_classes,
            metrics=metrics,
            requirements_met={
                "mAP50_ge_085": metrics.get("mAP50", 0.0) >= 0.85 if metrics else None,
                "supports_6_classes": num_classes == 6
            },
            supported_formats=list(settings.SUPPORTED_EXTENSIONS),
            max_resolution="8K (7680x4320)"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении информации о модели: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении информации о модели: {str(e)}"
        )

@router.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0, description="Порог уверенности для детекций")
):
    """
    Детекция объектов на изображении

    Args:
        file: Загруженное изображение
        conf: Порог уверенности (0.0-1.0)

    Returns:
        JSON с результатами детекции
    """
    # Валидация типа файла
    file_content = await file.read()
    file_extension = Path(file.filename or '').suffix.lower()

    # Проверка расширения файла
    is_supported_extension = file_extension in settings.SUPPORTED_EXTENSIONS
    is_supported_content_type = (
        file.content_type and (
            file.content_type in settings.SUPPORTED_IMAGE_FORMATS or
            file.content_type.startswith('image/')
        )
    )

    if not (is_supported_extension or is_supported_content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Поддерживаются: JPG, PNG, TIFF, RAW (DJI, Autel и др.). "
                  f"Получен: {file.content_type or 'unknown'}, расширение: {file_extension}"
        )

    # Валидация размера файла
    max_size = (
        settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_extension in settings.RAW_EXTENSIONS
        else settings.MAX_FILE_SIZE_STANDARD_MB * 1024 * 1024
    )
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Размер файла не должен превышать {max_size / 1024 / 1024:.0f}MB"
        )

    try:
        # Чтение изображения
        image = None

        # Попытка открыть через PIL
        try:
            image = Image.open(io.BytesIO(file_content))
        except Exception as pil_error:
            # Для RAW форматов используем rawpy или imageio
            if file_extension in settings.RAW_EXTENSIONS:
                logger.info(f"Попытка обработки RAW формата через rawpy/imageio: {file_extension}")
                try:
                    import rawpy
                    import numpy as np
                    # Сохраняем во временный файл для rawpy
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                        tmp_file.write(file_content)
                        tmp_path = tmp_file.name

                    try:
                        with rawpy.imread(tmp_path) as raw:
                            rgb = raw.postprocess()  # Конвертация в RGB
                            image = Image.fromarray(rgb)
                            logger.info(f"RAW файл успешно обработан через rawpy")
                    finally:
                        os.unlink(tmp_path)  # Удаляем временный файл
                except ImportError:
                    logger.warning("rawpy не установлен, пробуем imageio")
                    try:
                        import imageio
                        # imageio может работать с байтами для некоторых форматов
                        image = Image.fromarray(imageio.imread(io.BytesIO(file_content)))
                        logger.info(f"RAW файл успешно обработан через imageio")
                    except Exception as imageio_error:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Не удалось обработать RAW формат. "
                                  f"PIL ошибка: {str(pil_error)}, "
                                  f"rawpy ошибка: {str(imageio_error) if 'imageio' in locals() else 'N/A'}. "
                                  f"Убедитесь, что установлены rawpy и imageio."
                        )
                except Exception as raw_error:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ошибка обработки RAW файла: {str(raw_error)}"
                    )
            else:
                # Для других форматов пробрасываем ошибку PIL
                raise HTTPException(
                    status_code=400,
                    detail=f"Не удалось открыть изображение: {str(pil_error)}"
                )

        # Проверка разрешения
        if image.size[0] > settings.MAX_RESOLUTION or image.size[1] > settings.MAX_RESOLUTION:
            logger.warning(f"Большое разрешение: {image.size}. Может потребоваться больше времени на обработку.")

        if image.mode != 'RGB':
            image = image.convert('RGB')

        logger.info(f"Обработка изображения: {file.filename}, размер: {image.size}, conf={conf}")

        # Получение предсказаний
        pred = get_predictor()
        # Временно обновляем порог уверенности
        original_conf = pred.conf_threshold
        pred.conf_threshold = conf
        results = pred.predict(image)
        pred.conf_threshold = original_conf

        logger.info(f"Найдено объектов: {results['total_objects']}, дефектов: {results['defects_count']}")

        # Pydantic автоматически обработает alias "class" при создании из словаря
        return PredictResponse(**results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке изображения: {str(e)}"
        )

@router.post("/predict/batch", response_model=BatchPredictResponse)
async def batch_predict(
    files: List[UploadFile] = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0, description="Порог уверенности для детекций")
):
    """
    Batch детекция объектов на изображениях
    
    Args:
        files: Список загруженных изображений
        conf: Порог уверенности (0.0-1.0)
    
    Returns:
        JSON с результатами детекции для каждого изображения
    """
    if not files:
        raise HTTPException(status_code=400, detail="Не переданы файлы для анализа")
    
    results = []
    errors = []
    failed_count = 0

    for idx, file in enumerate(files):
        try:
            # Валидация типа файла
            file_content = await file.read()
            file_extension = Path(file.filename or '').suffix.lower()

            # Проверка расширения файла
            is_supported_extension = file_extension in settings.SUPPORTED_EXTENSIONS
            is_supported_content_type = (
                file.content_type and (
                    file.content_type in settings.SUPPORTED_IMAGE_FORMATS or
                    file.content_type.startswith('image/')
                )
            )

            if not (is_supported_extension or is_supported_content_type):
                raise ValueError(
                    f"Неподдерживаемый формат файла. Поддерживаются: JPG, PNG, TIFF, RAW. "
                    f"Получен: {file.content_type or 'unknown'}, расширение: {file_extension}"
                )

            # Валидация размера файла
            max_size = (
                settings.MAX_FILE_SIZE_MB * 1024 * 1024
                if file_extension in settings.RAW_EXTENSIONS
                else settings.MAX_FILE_SIZE_STANDARD_MB * 1024 * 1024
            )
            if len(file_content) > max_size:
                raise ValueError(f"Размер файла не должен превышать {max_size / 1024 / 1024:.0f}MB")

            # Чтение изображения
            image = None

            # Попытка открыть через PIL
            try:
                image = Image.open(io.BytesIO(file_content))
            except Exception as pil_error:
                # Для RAW форматов используем rawpy или imageio
                if file_extension in settings.RAW_EXTENSIONS:
                    logger.info(f"Попытка обработки RAW формата через rawpy/imageio: {file_extension}")
                    try:
                        import rawpy
                        import numpy as np
                        # Сохраняем во временный файл для rawpy
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                            tmp_file.write(file_content)
                            tmp_path = tmp_file.name

                        try:
                            with rawpy.imread(tmp_path) as raw:
                                rgb = raw.postprocess()  # Конвертация в RGB
                                image = Image.fromarray(rgb)
                                logger.info(f"RAW файл успешно обработан через rawpy")
                        finally:
                            os.unlink(tmp_path)  # Удаляем временный файл
                    except ImportError:
                        logger.warning("rawpy не установлен, пробуем imageio")
                        try:
                            import imageio
                            image = Image.fromarray(imageio.imread(io.BytesIO(file_content)))
                            logger.info(f"RAW файл успешно обработан через imageio")
                        except Exception as imageio_error:
                            raise ValueError(
                                f"Не удалось обработать RAW формат. "
                                f"PIL ошибка: {str(pil_error)}, "
                                f"imageio ошибка: {str(imageio_error)}"
                            )
                    except Exception as raw_error:
                        raise ValueError(f"Ошибка обработки RAW файла: {str(raw_error)}")
                else:
                    raise ValueError(f"Не удалось открыть изображение: {str(pil_error)}")

            # Проверка разрешения
            if image.size[0] > settings.MAX_RESOLUTION or image.size[1] > settings.MAX_RESOLUTION:
                logger.warning(f"Большое разрешение: {image.size}. Может потребоваться больше времени на обработку.")

            if image.mode != 'RGB':
                image = image.convert('RGB')

            logger.info(f"Обработка изображения {idx+1}/{len(files)}: {file.filename}, размер: {image.size}, conf={conf}")

            # Получение предсказаний
            pred = get_predictor()
            # Временно обновляем порог уверенности
            original_conf = pred.conf_threshold
            pred.conf_threshold = conf
            result = pred.predict(image)
            pred.conf_threshold = original_conf

            logger.info(f"Найдено объектов: {result['total_objects']}, дефектов: {result['defects_count']}")

            results.append(PredictResponse(**result))

        except Exception as e:
            logger.error(f"Ошибка при обработке изображения {idx+1}: {str(e)}")
            failed_count += 1
            errors.append({
                "index": idx,
                "filename": file.filename,
                "error": str(e)
            })

    return BatchPredictResponse(
        results=results,
        total=len(results),
        failed=failed_count,
        errors=errors if errors else None
    )

