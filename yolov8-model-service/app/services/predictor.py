"""
Модуль для инференса YOLOv8 модели
"""
import os
import torch

# КРИТИЧНО: Установить переменную окружения ДО импорта ultralytics
# PyTorch 2.6+ требует weights_only=False для загрузки YOLOv8 моделей
os.environ['TORCH_ALLOW_UNSAFE_LOAD'] = '1'

# Monkey patch для torch.load (на случай если переменная окружения не сработает)
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

from ultralytics import YOLO
from PIL import Image
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Маппинг классов
CLASS_NAMES = {
    0: "vibration_damper",
    1: "festoon_insulators",
    2: "traverse",
    3: "bad_insulator",
    4: "damaged_insulator",
    5: "polymer_insulators"
}

# Русские названия для отображения
CLASS_NAMES_RU = {
    "vibration_damper": "Виброгаситель",
    "festoon_insulators": "Гирлянда изоляторов",
    "traverse": "Траверса",
    "bad_insulator": "Изолятор отсутствует",
    "damaged_insulator": "Поврежденный изолятор",
    "polymer_insulators": "Полимерные изоляторы"
}

# Категории дефектов
DEFECT_CLASSES = ["bad_insulator", "damaged_insulator"]

# Детальные признаки дефектов (для расширенного анализа)
DEFECT_FEATURES = {
    "bad_insulator": {
        "type": "отсутствует",
        "severity": "critical",
        "description": "Изолятор полностью отсутствует"
    },
    "damaged_insulator": {
        "type": "поврежден",
        "severity": "high",
        "description": "Изолятор имеет видимые повреждения (трещины, сколы, перекос)"
    }
}

# Описание состояния по умолчанию (когда дефектов нет)
NORMAL_STATE = {
    "type": "норма",
    "severity": "none",
    "description": "Признаков дефекта не обнаружено"
}

class YOLOPredictor:
    """Класс для предсказаний YOLOv8 модели"""

    def __init__(self, model_path: str, conf_threshold: float = 0.25):
        """
        Инициализация предиктора

        Args:
            model_path: путь к файлу модели .pt
            conf_threshold: порог уверенности для детекций
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        logger.info(f"✅ Модель загружена: {model_path}")

    def predict(self, image: Image.Image, return_visualization: bool = False) -> Dict[str, Any]:
        """
        Предсказание на изображении

        Args:
            image: PIL Image
            return_visualization: вернуть визуализацию с bbox (опционально)

        Returns:
            Словарь с результатами детекции
        """
        # Предсказание
        results = self.model(image, conf=self.conf_threshold)

        # Парсинг результатов
        detections = []
        statistics = {name: 0 for name in CLASS_NAMES.values()}
        defects_count = 0

        # Визуализация (если нужно)
        annotated_image = None
        if return_visualization:
            annotated_image = results[0].plot()  # YOLOv8 автоматически рисует bbox
            annotated_image = Image.fromarray(annotated_image)

        for result in results:
            boxes = result.boxes

            for box in boxes:
                # Координаты bbox
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # Класс и уверенность
                cls_id = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())

                # Название класса
                class_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")

                # Размер объекта (для определения малых объектов <30px)
                bbox_width = int(x2 - x1)
                bbox_height = int(y2 - y1)
                bbox_area = bbox_width * bbox_height
                is_small_object = bbox_width < 30 or bbox_height < 30

                # Признаки дефекта (для удовлетворения требований ТЗ)
                if class_name in DEFECT_CLASSES:
                    defect_info = DEFECT_FEATURES.get(class_name, {})
                else:
                    defect_info = NORMAL_STATE

                # Детекция
                detection = {
                    "class": class_name,
                    "class_ru": CLASS_NAMES_RU.get(class_name, class_name),
                    "confidence": round(conf, 4),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "bbox_size": {
                        "width": bbox_width,
                        "height": bbox_height,
                        "area": bbox_area,
                        "is_small": is_small_object
                    },
                    "defect_summary": {
                        "type": defect_info.get("type", "норма"),
                        "severity": defect_info.get("severity", "none"),
                        "description": defect_info.get("description", "")
                    }
                }

                # Добавляем признаки дефекта для дефектных классов
                if class_name in DEFECT_CLASSES:
                    detection["defect_features"] = {
                        "type": defect_info.get("type", "неизвестно"),
                        "severity": defect_info.get("severity", "medium"),
                        "description": defect_info.get("description", ""),
                        "confidence_level": "high" if conf > 0.7 else "medium" if conf > 0.5 else "low"
                    }

                detections.append(detection)

                # Обновляем статистику
                statistics[class_name] += 1

                # Подсчет дефектов
                if class_name in DEFECT_CLASSES:
                    defects_count += 1

        result_dict = {
            "detections": detections,
            "statistics": statistics,
            "total_objects": len(detections),
            "defects_count": defects_count,
            "has_defects": defects_count > 0
        }

        if return_visualization and annotated_image:
            result_dict["visualization"] = annotated_image

        return result_dict

