#!/usr/bin/env python3
"""
Автоматическое создание bbox для cropped изображений из InsPLAD fault datasets

Так как изображения уже CROPPED (объект занимает всё изображение),
мы создаём bbox на весь размер изображения с небольшим отступом.
"""

from pathlib import Path
from PIL import Image
import shutil
from typing import Dict, Tuple

# Маппинг InsPLAD fault классов → ваши классы
FAULT_CLASS_MAPPING = {
    # Из defect_supervised и unsupervised_anomaly_detection
    
    # КЛАСС 6: nest (bird-nest)
    'bird-nest': (6, 'nest'),
    'nest': (6, 'nest'),
    
    # КЛАСС 3: bad_insulator (rust/corrosion)
    'rust': (3, 'bad_insulator'),
    'corrosão': (3, 'bad_insulator'),  # Portuguese
    
    # КЛАСС 4: damaged_insulator (missing parts, torned)
    'missing-cap': (4, 'damaged_insulator'),
    'missingcap': (4, 'damaged_insulator'),
    'torned-up': (4, 'damaged_insulator'),
    'peeling-paint': (4, 'damaged_insulator'),
    
    # КЛАСС 0: vibration_damper (можем добавить good examples)
    # 'good' (damper-stockbridge) - опционально
    
    # КЛАСС 5: polymer_insulators (good examples)
    # 'good' (polymer-insulator) - опционально
    
    # КЛАСС 1: festoon_insulators (good examples)
    # 'good' (glass-insulator) - опционально
}


def create_full_image_bbox(
    image_path: Path,
    class_id: int,
    padding: float = 0.025
) -> str:
    """
    Создаёт YOLO bbox на весь размер изображения
    
    Args:
        image_path: Путь к изображению
        class_id: ID класса (0-7)
        padding: Отступ от краёв (0.025 = 2.5% с каждой стороны)
    
    Returns:
        YOLO format string: "class_id x_center y_center width height"
    """
    try:
        # Открываем изображение чтобы получить размеры
        img = Image.open(image_path)
        width, height = img.size
        img.close()
        
        # Создаём bbox с отступами
        # Центр всегда (0.5, 0.5) так как объект в центре
        x_center = 0.5
        y_center = 0.5
        
        # Размер bbox = почти всё изображение (с отступом)
        bbox_width = 1.0 - (2 * padding)
        bbox_height = 1.0 - (2 * padding)
        
        # Убедимся что в диапазоне [0, 1]
        x_center = max(0.0, min(1.0, x_center))
        y_center = max(0.0, min(1.0, y_center))
        bbox_width = max(0.0, min(1.0, bbox_width))
        bbox_height = max(0.0, min(1.0, bbox_height))
        
        return f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}\n"
    
    except Exception as e:
        print(f"❌ Ошибка создания bbox для {image_path}: {e}")
        return None


def process_fault_dataset(
    fault_dataset_dir: Path,
    output_dir: Path,
    dataset_name: str = "fault"
) -> Dict[str, int]:
    """
    Обрабатывает fault dataset и создаёт bbox для всех изображений
    
    Args:
        fault_dataset_dir: Путь к fault датасету (defect_supervised или unsupervised)
        output_dir: Папка для сохранения результатов
        dataset_name: Имя датасета для статистики
    
    Returns:
        Dict с статистикой по классам
    """
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'by_class': {}
    }
    
    print(f"\n📂 Обработка {dataset_name}: {fault_dataset_dir.name}")
    print("-" * 60)
    
    # Проходим по всем asset папкам
    for asset_dir in fault_dataset_dir.iterdir():
        if not asset_dir.is_dir():
            continue
        
        print(f"\n   📦 Asset: {asset_dir.name}")
        
        # Ищем train и test/val папки
        for split in ['train', 'test', 'val']:
            split_dir = asset_dir / split
            if not split_dir.exists():
                continue
            
            # Проходим по папкам с классами (good, rust, bird-nest, etc.)
            for class_dir in split_dir.iterdir():
                if not class_dir.is_dir():
                    continue
                
                class_name = class_dir.name
                
                # Проверяем маппинг
                if class_name not in FAULT_CLASS_MAPPING:
                    # Пропускаем good и другие ненужные классы
                    continue
                
                your_class_id, your_class_name = FAULT_CLASS_MAPPING[class_name]
                
                # Находим все изображения
                images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.JPG'))
                
                if not images:
                    continue
                
                print(f"      ✓ {class_name} → класс {your_class_id} ({your_class_name}): {len(images)} images")
                
                # Создаём выходные папки
                output_images_dir = output_dir / 'images' / split
                output_labels_dir = output_dir / 'labels' / split
                output_images_dir.mkdir(parents=True, exist_ok=True)
                output_labels_dir.mkdir(parents=True, exist_ok=True)
                
                # Обрабатываем каждое изображение
                for img_path in images:
                    try:
                        # Создаём bbox
                        bbox_line = create_full_image_bbox(img_path, your_class_id)
                        
                        if bbox_line is None:
                            stats['skipped'] += 1
                            continue
                        
                        # Уникальное имя файла
                        unique_name = f"{dataset_name}_{asset_dir.name}_{class_name}_{img_path.stem}{img_path.suffix}"
                        
                        # Копируем изображение
                        output_img_path = output_images_dir / unique_name
                        shutil.copy2(img_path, output_img_path)
                        
                        # Сохраняем label
                        output_label_path = output_labels_dir / f"{Path(unique_name).stem}.txt"
                        with open(output_label_path, 'w') as f:
                            f.write(bbox_line)
                        
                        stats['processed'] += 1
                        stats['by_class'][your_class_id] = stats['by_class'].get(your_class_id, 0) + 1
                    
                    except Exception as e:
                        print(f"         ❌ Ошибка {img_path.name}: {e}")
                        stats['skipped'] += 1
    
    return stats


def main():
    """Главная функция"""
    
    print("🤖 АВТОМАТИЧЕСКОЕ СОЗДАНИЕ BBOX для InsPLAD Fault Datasets")
    print("=" * 60)
    
    # Пути
    base_dir = Path('.')
    defect_supervised_dir = base_dir / 'defect_supervised'
    unsupervised_dir = base_dir / 'unsupervised_anomaly_detection'
    output_dir = base_dir / 'insplad_fault_with_bbox'
    
    # Проверка наличия датасетов
    if not defect_supervised_dir.exists() and not unsupervised_dir.exists():
        print("❌ Fault datasets не найдены!")
        print("   Ожидаются:")
        print(f"   - {defect_supervised_dir}")
        print(f"   - {unsupervised_dir}")
        return
    
    # Создаём выходную папку
    output_dir.mkdir(exist_ok=True)
    
    total_stats = {
        'processed': 0,
        'skipped': 0,
        'by_class': {}
    }
    
    # Обрабатываем defect_supervised
    if defect_supervised_dir.exists():
        stats1 = process_fault_dataset(
            defect_supervised_dir,
            output_dir,
            'defect_supervised'
        )
        total_stats['processed'] += stats1['processed']
        total_stats['skipped'] += stats1['skipped']
        for class_id, count in stats1['by_class'].items():
            total_stats['by_class'][class_id] = total_stats['by_class'].get(class_id, 0) + count
    
    # Обрабатываем unsupervised_anomaly_detection
    if unsupervised_dir.exists():
        stats2 = process_fault_dataset(
            unsupervised_dir,
            output_dir,
            'unsupervised'
        )
        total_stats['processed'] += stats2['processed']
        total_stats['skipped'] += stats2['skipped']
        for class_id, count in stats2['by_class'].items():
            total_stats['by_class'][class_id] = total_stats['by_class'].get(class_id, 0) + count
    
    # Финальная статистика
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Обработано: {total_stats['processed']}")
    print(f"   Пропущено: {total_stats['skipped']}")
    
    print(f"\n📈 ПО КЛАССАМ:")
    class_names = {
        0: 'vibration_damper',
        1: 'festoon_insulators',
        2: 'traverse',
        3: 'bad_insulator',
        4: 'damaged_insulator',
        5: 'polymer_insulators',
        6: 'nest',
        7: 'safety_sign'
    }
    
    for class_id in sorted(total_stats['by_class'].keys()):
        count = total_stats['by_class'][class_id]
        class_name = class_names.get(class_id, 'unknown')
        print(f"   Класс {class_id} ({class_name:25s}): {count:4d} images")
    
    print(f"\n📂 Результаты сохранены в: {output_dir}/")
    print("   Структура:")
    print("   ├── images/")
    print("   │   ├── train/")
    print("   │   ├── val/")
    print("   │   └── test/")
    print("   └── labels/")
    print("       ├── train/")
    print("       ├── val/")
    print("       └── test/")
    
    print("\n💡 СЛЕДУЮЩИЙ ШАГ:")
    print("   Запустите merge_insplad_dataset.py для объединения всех датасетов")


if __name__ == '__main__':
    main()

