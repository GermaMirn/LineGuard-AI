#!/usr/bin/env python3
"""
Объединение InsPLAD датасета с вашим датасетом
Маппинг классов InsPLAD → ваши 8 классов

АНАЛИЗ InsPLAD-det:
- 18 классов
- ~10,600 изображений
- ~29,000 аннотаций

ВАЖНО: InsPLAD-det НЕ содержит:
- ❌ bird_nest (класс 6) - есть только в InsPLAD-fault
- ❌ safety_sign (класс 7) - отсутствует полностью
- ❌ Defect классы (3,4) - есть только в InsPLAD-fault
"""

from pathlib import Path
import shutil
import json
import random
from collections import defaultdict

# Маппинг InsPLAD классов → ваши классы
# Основано на реальном анализе InsPLAD-det датасета
INSPLAD_TO_YOUR_CLASSES = {
    # InsPLAD ID → (ваш_класс_id, ваш_класс_name, InsPLAD_name)
    
    # Vibration dampers (ОТЛИЧНОЕ покрытие!)
    4: (0, 'vibration_damper', 'stockbridge damper'),      # 6,953 instances
    17: (0, 'vibration_damper', 'spiral damper'),          # 1,020 instances
    
    # Insulators - glass (хорошее покрытие)
    8: (1, 'festoon_insulators', 'glass insulator'),       # 2,978 instances
    2: (1, 'festoon_insulators', 'yoke suspension'),       # 6,520 instances (подвесы)
    
    # Polymer insulators (ОТЛИЧНОЕ покрытие!)
    7: (5, 'polymer_insulators', 'polymer insulator'),     # 3,244 instances
    
    # Дополнительные (опционально, можно включить/выключить)
    # 11: (5, 'polymer_insulators', 'polymer insulator lower shackle'),  # 1,842
    # 12: (5, 'polymer_insulators', 'polymer insulator upper shackle'),  # 1,692
    
    # НЕ МАППИМ (нет соответствия):
    # 1: yoke - не нужен
    # 3: spacer - не нужен
    # 5,6: lightning rod - не нужен
    # 9: tower id plate - не нужен
    # 10: vari-grip - не нужен
    # 13-16: shackles - мелкие детали, не нужны
    # 18: sphere - не нужен
}


def convert_coco_to_yolo(coco_annotation, image_info, category_id_map):
    """
    Конвертирует COCO bbox в YOLO format
    
    Args:
        coco_annotation: COCO annotation dict
        image_info: Image metadata from COCO
        category_id_map: Dict mapping COCO category_id → (your_class_id, name)
    
    Returns:
        YOLO format string или None если класс не нужен
    """
    category_id = coco_annotation['category_id']
    
    # Проверяем маппинг
    if category_id not in category_id_map:
        return None
    
    your_class_id, your_class_name, _ = category_id_map[category_id]
    
    # COCO bbox: [x, y, width, height] (абсолютные координаты)
    x, y, w, h = coco_annotation['bbox']
    
    # Размеры изображения
    img_width = image_info['width']
    img_height = image_info['height']
    
    # Конвертируем в YOLO format: [x_center, y_center, width, height] (нормализованные)
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    norm_width = w / img_width
    norm_height = h / img_height
    
    # Проверка границ [0, 1]
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    norm_width = max(0.0, min(1.0, norm_width))
    norm_height = max(0.0, min(1.0, norm_height))
    
    return f"{your_class_id} {x_center:.6f} {y_center:.6f} {norm_width:.6f} {norm_height:.6f}\n"


def merge_insplad_dataset(insplad_dir: Path, your_dataset_dir: Path):
    """
    Объединяет InsPLAD с вашим датасетом
    
    Args:
        insplad_dir: Путь к распакованному InsPLAD-det
        your_dataset_dir: Путь к вашему dataset_8classes
    """
    
    print("🔄 ОБЪЕДИНЕНИЕ InsPLAD С ВАШИМ ДАТАСЕТОМ")
    print("="*60)
    
    if not insplad_dir.exists():
        print(f"❌ InsPLAD не найден: {insplad_dir}")
        print("   Скачайте InsPLAD-det.zip и распакуйте:")
        print("   https://github.com/andreluizbvs/InsPLAD")
        return
    
    print("\n📋 ШАГ 1: Изучите структуру InsPLAD")
    print(f"   InsPLAD папка: {insplad_dir}")
    print("   Найдите:")
    print("   - classes.txt или similar (список классов)")
    print("   - images/ (папка с изображениями)")
    print("   - labels/ (папка с аннотациями)")
    
    print("\n📋 ШАГ 2: Обновите INSPLAD_TO_YOUR_CLASSES маппинг")
    print("   После того как узнаете имена классов InsPLAD")
    
    print("\n📋 ШАГ 3: Запустите скрипт снова")
    print("   python merge_insplad_dataset.py")
    
    print("\n💡 РЕКОМЕНДАЦИЯ:")
    print("   Сначала проверьте InsPLAD документацию:")
    print("   https://andreluizbvs.github.io/InsPLAD/")
    
    # TODO: Реализовать после изучения структуры InsPLAD
    
    print("\n" + "="*60)


def main():
    """Главная функция"""
    
    # Пути
    insplad_dir = Path('InsPLAD-det')  # Путь к распакованному InsPLAD
    your_dataset_dir = Path('dataset_8classes')
    
    merge_insplad_dataset(insplad_dir, your_dataset_dir)
    
    print("\n✅ ПЛАН ДЕЙСТВИЙ:")
    print("   1. Скачайте InsPLAD-det.zip с GitHub")
    print("   2. Распакуйте в папку InsPLAD-det/")
    print("   3. Изучите структуру и классы")
    print("   4. Обновите маппинг в этом скрипте")
    print("   5. Запустите снова для объединения")


if __name__ == '__main__':
    main()

