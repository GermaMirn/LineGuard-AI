#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ СКРИПТ: Объединение всех InsPLAD датасетов с вашим dataset_8classes

Объединяет:
1. InsPLAD-det (COCO → YOLO) → классы 0, 1, 5
2. insplad_fault_with_bbox → классы 3, 4, 6
3. Ваш dataset_8classes → все классы

Результат: Обновлённый dataset_8classes с ~32,000+ изображений
"""

from pathlib import Path
import json
import shutil
from collections import defaultdict
import random

# Маппинг InsPLAD-det классов → ваши классы
INSPLAD_DET_MAPPING = {
    # Vibration dampers
    4: (0, 'vibration_damper'),     # stockbridge damper
    17: (0, 'vibration_damper'),    # spiral damper

    # Insulators - glass
    8: (1, 'festoon_insulators'),   # glass insulator
    2: (1, 'festoon_insulators'),   # yoke suspension

    # Polymer insulators
    7: (5, 'polymer_insulators'),   # polymer insulator
}


def convert_coco_to_yolo(annotation, image_info, category_mapping):
    """Конвертирует COCO bbox в YOLO format"""
    category_id = annotation['category_id']

    if category_id not in category_mapping:
        return None

    your_class_id, your_class_name = category_mapping[category_id]

    # COCO: [x, y, width, height] (top-left corner)
    x, y, w, h = annotation['bbox']
    img_w = image_info['width']
    img_h = image_info['height']

    # YOLO: [x_center, y_center, width, height] (normalized)
    x_center = (x + w / 2) / img_w
    y_center = (y + h / 2) / img_h
    norm_w = w / img_w
    norm_h = h / img_h

    # Clamp to [0, 1]
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    norm_w = max(0.0, min(1.0, norm_w))
    norm_h = max(0.0, min(1.0, norm_h))

    return f"{your_class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}"


def process_insplad_det(insplad_dir, output_dir):
    """Обрабатывает InsPLAD-det (COCO → YOLO)"""

    print("\n" + "="*60)
    print("📦 ОБРАБОТКА InsPLAD-det")
    print("="*60)

    stats = {'processed': 0, 'skipped': 0, 'by_class': defaultdict(int)}

    # Обрабатываем train и val
    for split in ['train', 'val']:
        coco_file = insplad_dir / 'annotations' / f'instances_{split}.json'
        images_dir = insplad_dir / split

        if not coco_file.exists():
            print(f"⚠️ Пропускаем {split}: {coco_file} не найден")
            continue

        print(f"\n📂 Обработка {split}...")

        # Читаем COCO annotations
        with open(coco_file, 'r') as f:
            coco_data = json.load(f)

        # Создаём маппинг image_id → image_info
        images_map = {img['id']: img for img in coco_data['images']}

        # Группируем annotations по image_id
        annotations_by_image = defaultdict(list)
        for ann in coco_data['annotations']:
            annotations_by_image[ann['image_id']].append(ann)

        # Обрабатываем каждое изображение
        for image_id, image_info in images_map.items():
            image_filename = image_info['file_name']
            image_path = images_dir / image_filename

            if not image_path.exists():
                stats['skipped'] += 1
                continue

            # Конвертируем все annotations для этого изображения
            yolo_lines = []
            for ann in annotations_by_image.get(image_id, []):
                yolo_line = convert_coco_to_yolo(ann, image_info, INSPLAD_DET_MAPPING)
                if yolo_line:
                    yolo_lines.append(yolo_line)
                    class_id = int(yolo_line.split()[0])
                    stats['by_class'][class_id] += 1

            # Пропускаем изображения без релевантных объектов
            if not yolo_lines:
                stats['skipped'] += 1
                continue

            # Копируем изображение
            output_img_dir = output_dir / 'images' / split
            output_img_dir.mkdir(parents=True, exist_ok=True)

            unique_name = f"insplad_det_{split}_{image_filename}"
            output_img_path = output_img_dir / unique_name
            shutil.copy2(image_path, output_img_path)

            # Сохраняем label
            output_label_dir = output_dir / 'labels' / split
            output_label_dir.mkdir(parents=True, exist_ok=True)

            label_filename = Path(unique_name).stem + '.txt'
            output_label_path = output_label_dir / label_filename

            with open(output_label_path, 'w') as f:
                f.write('\n'.join(yolo_lines) + '\n')

            stats['processed'] += 1

        print(f"   ✓ Обработано: {stats['processed']} images")

    return stats


def merge_fault_dataset(fault_dir, output_dir):
    """Копирует insplad_fault_with_bbox в output"""

    print("\n" + "="*60)
    print("📦 ОБЪЕДИНЕНИЕ insplad_fault_with_bbox")
    print("="*60)

    stats = {'processed': 0, 'skipped': 0, 'by_class': defaultdict(int)}

    if not fault_dir.exists():
        print("⚠️ insplad_fault_with_bbox не найден, пропускаем")
        return stats

    # Копируем все splits
    for split in ['train', 'val', 'test']:
        images_dir = fault_dir / 'images' / split
        labels_dir = fault_dir / 'labels' / split

        if not images_dir.exists():
            continue

        print(f"\n📂 Копирование {split}...")

        # Находим все изображения
        for img_path in images_dir.glob('*.jpg'):
            label_path = labels_dir / f"{img_path.stem}.txt"

            if not label_path.exists():
                stats['skipped'] += 1
                continue

            # Копируем изображение
            output_img_dir = output_dir / 'images' / split
            output_img_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_path, output_img_dir / img_path.name)

            # Копируем label
            output_label_dir = output_dir / 'labels' / split
            output_label_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(label_path, output_label_dir / label_path.name)

            # Статистика
            with open(label_path, 'r') as f:
                for line in f:
                    class_id = int(line.split()[0])
                    stats['by_class'][class_id] += 1

            stats['processed'] += 1

        print(f"   ✓ Скопировано: {stats['processed']} images")

    return stats


def merge_with_existing_dataset(source_dir, target_dir):
    """Объединяет новые данные с существующим dataset_8classes"""

    print("\n" + "="*60)
    print("📦 ОБЪЕДИНЕНИЕ С dataset_8classes")
    print("="*60)

    if not target_dir.exists():
        print(f"⚠️ {target_dir} не существует, создаём новый")
        target_dir.mkdir(parents=True)

    stats = {'copied': 0}

    # Копируем все новые данные
    for split in ['train', 'val', 'test']:
        source_img_dir = source_dir / 'images' / split
        source_label_dir = source_dir / 'labels' / split

        if not source_img_dir.exists():
            continue

        target_img_dir = target_dir / 'images' / split
        target_label_dir = target_dir / 'labels' / split

        target_img_dir.mkdir(parents=True, exist_ok=True)
        target_label_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📂 Объединение {split}...")

        # Копируем изображения
        for img_path in source_img_dir.glob('*.jpg'):
            target_img_path = target_img_dir / img_path.name

            # Если файл уже существует, добавляем prefix
            if target_img_path.exists():
                target_img_path = target_img_dir / f"new_{img_path.name}"

            shutil.copy2(img_path, target_img_path)
            stats['copied'] += 1

        # Копируем labels
        for label_path in source_label_dir.glob('*.txt'):
            target_label_path = target_label_dir / label_path.name

            if target_label_path.exists():
                target_label_path = target_label_dir / f"new_{label_path.name}"

            shutil.copy2(label_path, target_label_path)

        print(f"   ✓ Добавлено: {stats['copied']} images")

    return stats


def main():
    """Главная функция"""

    print("🔄 ФИНАЛЬНОЕ ОБЪЕДИНЕНИЕ ВСЕХ ДАТАСЕТОВ")
    print("="*60)

    # Пути
    base_dir = Path('.')
    insplad_det_dir = base_dir / 'InsPLAD-det'
    fault_dir = base_dir / 'insplad_fault_with_bbox'
    temp_dir = base_dir / 'temp_insplad_merged'
    final_dir = base_dir / 'dataset_8classes'

    # Создаём временную папку для объединения InsPLAD данных
    temp_dir.mkdir(exist_ok=True)

    # 1. Обрабатываем InsPLAD-det
    stats_det = {'processed': 0, 'by_class': defaultdict(int)}
    if insplad_det_dir.exists():
        stats_det = process_insplad_det(insplad_det_dir, temp_dir)
    else:
        print("\n⚠️ InsPLAD-det не найден, пропускаем")

    # 2. Копируем fault dataset
    stats_fault = {'processed': 0, 'by_class': defaultdict(int)}
    if fault_dir.exists():
        stats_fault = merge_fault_dataset(fault_dir, temp_dir)
    else:
        print("\n⚠️ insplad_fault_with_bbox не найден, пропускаем")

    # 3. Объединяем с существующим dataset_8classes
    print("\n" + "="*60)
    print("📦 Финальное объединение...")
    print("="*60)

    merge_with_existing_dataset(temp_dir, final_dir)

    # 4. Копируем YAML конфиг
    yaml_source = base_dir / 'dataset_8classes.yaml'
    yaml_target = final_dir / 'dataset_8classes.yaml'
    if yaml_source.exists() and not yaml_target.exists():
        shutil.copy2(yaml_source, yaml_target)

    # 5. Удаляем временную папку
    print("\n🗑️ Очистка временных файлов...")
    shutil.rmtree(temp_dir)

    # ФИНАЛЬНАЯ СТАТИСТИКА
    print("\n" + "="*60)
    print("✅ ОБЪЕДИНЕНИЕ ЗАВЕРШЕНО!")
    print("="*60)

    print(f"\n📊 ДОБАВЛЕНО ИЗ InsPLAD:")
    print(f"   InsPLAD-det: {stats_det['processed']} images")
    print(f"   Fault datasets: {stats_fault['processed']} images")
    print(f"   ИТОГО добавлено: {stats_det['processed'] + stats_fault['processed']} images")

    print(f"\n📈 ДОБАВЛЕНО ПО КЛАССАМ (InsPLAD-det):")
    class_names = {
        0: 'vibration_damper',
        1: 'festoon_insulators',
        5: 'polymer_insulators',
    }
    for class_id in sorted(stats_det['by_class'].keys()):
        count = stats_det['by_class'][class_id]
        name = class_names.get(class_id, 'unknown')
        print(f"   Класс {class_id} ({name:25s}): +{count:5d}")

    print(f"\n📈 ДОБАВЛЕНО ПО КЛАССАМ (Fault):")
    fault_names = {
        3: 'bad_insulator',
        4: 'damaged_insulator',
        6: 'nest',
    }
    for class_id in sorted(stats_fault['by_class'].keys()):
        count = stats_fault['by_class'][class_id]
        name = fault_names.get(class_id, 'unknown')
        print(f"   Класс {class_id} ({name:25s}): +{count:5d}")

    # Проверяем финальную статистику
    print(f"\n📊 ФИНАЛЬНЫЙ ДАТАСЕТ:")
    for split in ['train', 'val', 'test']:
        split_dir = final_dir / 'images' / split
        if split_dir.exists():
            count = len(list(split_dir.glob('*.jpg')))
            print(f"   {split:6s}: {count:5d} images")

    print(f"\n📂 Результат: {final_dir}/")
    print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
    print("   1. Исправить corrupt labels: python data_preparation/fix_corrupt_labels.py")
    print("   2. Создать архив: tar -czf dataset_8classes_final.tar.gz --no-xattrs dataset_8classes/")
    print("   3. Загрузить в Google Drive и обучить!")


if __name__ == '__main__':
    main()

