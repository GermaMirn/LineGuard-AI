#!/usr/bin/env python3
"""
Скрипт для добавления внешних датасетов в dataset_8classes

Поддерживает:
1. Датасеты в YOLO format (images/ + labels/)
2. Автоматический маппинг классов
3. Распределение по train/val/test
4. Проверку и фиксацию corrupt labels
"""

from pathlib import Path
import shutil
import random
from collections import defaultdict
import argparse


# Маппинг имён классов из внешних датасетов → ваши классы
CLASS_MAPPING = {
    # Damaged insulator synonyms
    'damaged_insulator': 4,
    'broken_insulator': 4,
    'defective_insulator': 4,
    'cracked_insulator': 4,
    'insulator_damage': 4,
    
    # Nest synonyms
    'bird_nest': 6,
    'nest': 6,
    'bird': 6,  # если только гнёзда
    
    # Safety sign synonyms
    'safety_sign': 7,
    'warning_sign': 7,
    'hazard_sign': 7,
    'electrical_sign': 7,
    
    # Vibration damper (если вдруг)
    'vibration_damper': 0,
    'damper': 0,
    'stockbridge': 0,
    
    # Insulators
    'festoon_insulators': 1,
    'glass_insulator': 1,
    'insulator': 1,
    
    # Traverse
    'traverse': 2,
    'crossarm': 2,
    
    # Bad insulator
    'bad_insulator': 3,
    'rust_insulator': 3,
    'corrosion': 3,
    
    # Polymer insulator
    'polymer_insulator': 5,
    'polymer_insulators': 5,
}


def remap_label_file(label_path: Path, class_mapping_dict: dict, 
                     external_class_names: dict) -> list[str]:
    """
    Перемаппивает class IDs в label файле
    
    Args:
        label_path: Путь к label файлу
        class_mapping_dict: Маппинг имён классов → ваш ID
        external_class_names: {external_id: external_name}
    
    Returns:
        Список строк для нового label файла (или пустой, если нет подходящих классов)
    """
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        remapped_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 5:
                continue
            
            external_class_id = int(parts[0])
            coords = parts[1:5]
            
            # Получаем имя внешнего класса
            external_class_name = external_class_names.get(external_class_id, '').lower()
            
            # Маппим на ваш класс
            your_class_id = class_mapping_dict.get(external_class_name)
            
            if your_class_id is not None:
                # Проверяем координаты
                try:
                    coords_float = [float(c) for c in coords]
                    # Clamp to [0, 1]
                    coords_float = [max(0.0, min(1.0, c)) for c in coords_float]
                    
                    remapped_line = f"{your_class_id} {' '.join(f'{c:.6f}' for c in coords_float)}\n"
                    remapped_lines.append(remapped_line)
                except ValueError:
                    continue
        
        return remapped_lines
    
    except Exception as e:
        print(f"❌ Ошибка обработки {label_path}: {e}")
        return []


def merge_external_dataset(external_dir: Path, 
                           your_dataset_dir: Path,
                           external_class_names: dict,
                           train_split: float = 0.8,
                           val_split: float = 0.15):
    """
    Добавляет внешний датасет в ваш dataset_8classes
    
    Args:
        external_dir: Путь к внешнему датасету (должен содержать images/ и labels/)
        your_dataset_dir: Путь к dataset_8classes
        external_class_names: Маппинг {class_id: class_name} для внешнего датасета
        train_split: Доля для train (по умолчанию 80%)
        val_split: Доля для val (по умолчанию 15%, остальное - test)
    """
    
    print("\n" + "="*70)
    print(f"🔄 ДОБАВЛЕНИЕ ВНЕШНЕГО ДАТАСЕТА")
    print("="*70)
    print(f"   Источник: {external_dir}")
    print(f"   Цель: {your_dataset_dir}")
    print()
    
    # Проверяем структуру внешнего датасета
    external_images = external_dir / 'images'
    external_labels = external_dir / 'labels'
    
    if not external_images.exists():
        print(f"❌ Не найдена папка images: {external_images}")
        return
    
    if not external_labels.exists():
        print(f"❌ Не найдена папка labels: {external_labels}")
        return
    
    # Собираем все изображения из внешнего датасета
    all_images = []
    
    # Проверяем структуру: images/ может содержать train/val/test или файлы напрямую
    if list((external_images / 'train').glob('*')) if (external_images / 'train').exists() else []:
        # Структура с split
        for split in ['train', 'val', 'test']:
            split_dir = external_images / split
            if split_dir.exists():
                all_images.extend(list(split_dir.glob('*.jpg')) + 
                                list(split_dir.glob('*.png')) +
                                list(split_dir.glob('*.jpeg')))
    else:
        # Плоская структура
        all_images = (list(external_images.glob('*.jpg')) + 
                     list(external_images.glob('*.png')) +
                     list(external_images.glob('*.jpeg')))
    
    print(f"📊 Найдено изображений: {len(all_images)}")
    
    if not all_images:
        print("⚠️ Нет изображений для добавления")
        return
    
    # Перемешиваем для случайного split
    random.shuffle(all_images)
    
    # Вычисляем размеры split
    n_total = len(all_images)
    n_train = int(n_total * train_split)
    n_val = int(n_total * val_split)
    
    splits = {
        'train': all_images[:n_train],
        'val': all_images[n_train:n_train + n_val],
        'test': all_images[n_train + n_val:]
    }
    
    print(f"📂 Распределение:")
    print(f"   Train: {len(splits['train'])} images")
    print(f"   Val:   {len(splits['val'])} images")
    print(f"   Test:  {len(splits['test'])} images")
    print()
    
    stats = {
        'added': 0,
        'skipped': 0,
        'by_class': defaultdict(int)
    }
    
    # Обрабатываем каждый split
    for split_name, images in splits.items():
        print(f"🔄 Обработка {split_name}...")
        
        target_img_dir = your_dataset_dir / 'images' / split_name
        target_label_dir = your_dataset_dir / 'labels' / split_name
        
        target_img_dir.mkdir(parents=True, exist_ok=True)
        target_label_dir.mkdir(parents=True, exist_ok=True)
        
        for img_path in images:
            # Ищем соответствующий label
            # Может быть в labels/ или labels/train/ etc
            label_name = img_path.stem + '.txt'
            
            possible_label_paths = [
                external_labels / split_name / label_name,
                external_labels / label_name,
                img_path.parent.parent / 'labels' / split_name / label_name,
                img_path.parent.parent / 'labels' / label_name,
            ]
            
            label_path = None
            for p in possible_label_paths:
                if p.exists():
                    label_path = p
                    break
            
            if not label_path:
                stats['skipped'] += 1
                continue
            
            # Перемаппиваем label
            remapped_lines = remap_label_file(label_path, CLASS_MAPPING, external_class_names)
            
            if not remapped_lines:
                stats['skipped'] += 1
                continue
            
            # Генерируем уникальное имя
            unique_name = f"ext_{external_dir.name}_{img_path.name}"
            target_img_path = target_img_dir / unique_name
            target_label_path = target_label_dir / (Path(unique_name).stem + '.txt')
            
            # Копируем изображение
            shutil.copy2(img_path, target_img_path)
            
            # Сохраняем remapped label
            with open(target_label_path, 'w') as f:
                f.writelines(remapped_lines)
            
            # Статистика
            for line in remapped_lines:
                class_id = int(line.split()[0])
                stats['by_class'][class_id] += 1
            
            stats['added'] += 1
        
        print(f"   ✓ Добавлено: {stats['added']} images")
    
    # Финальная статистика
    print("\n" + "="*70)
    print("✅ ДОБАВЛЕНИЕ ЗАВЕРШЕНО")
    print("="*70)
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Добавлено: {stats['added']} images")
    print(f"   Пропущено: {stats['skipped']} images")
    
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
    
    for class_id in sorted(stats['by_class'].keys()):
        count = stats['by_class'][class_id]
        name = class_names.get(class_id, 'unknown')
        print(f"   Класс {class_id} ({name:25s}): +{count:5d} objects")
    
    print(f"\n💡 СЛЕДУЮЩИЕ ШАГИ:")
    print("   1. Запустите fix_corrupt_labels.py для проверки")
    print("   2. Пересоздайте архив dataset_8classes_final.tar.gz")
    print("   3. Загрузите в Google Drive и обучайте!")


def main():
    parser = argparse.ArgumentParser(description='Добавить внешний датасет в dataset_8classes')
    parser.add_argument('external_dir', type=str, help='Путь к внешнему датасету')
    parser.add_argument('--classes', type=str, required=True, 
                       help='Маппинг классов в формате: 0:damaged_insulator,1:nest,2:safety_sign')
    parser.add_argument('--train-split', type=float, default=0.8, 
                       help='Доля train (по умолчанию 0.8)')
    parser.add_argument('--val-split', type=float, default=0.15, 
                       help='Доля val (по умолчанию 0.15)')
    
    args = parser.parse_args()
    
    # Парсим маппинг классов
    external_class_names = {}
    for pair in args.classes.split(','):
        class_id, class_name = pair.split(':')
        external_class_names[int(class_id)] = class_name.strip()
    
    print(f"\n📋 Маппинг классов внешнего датасета:")
    for cid, cname in external_class_names.items():
        your_id = CLASS_MAPPING.get(cname.lower(), '???')
        print(f"   {cid}: {cname} → ваш класс {your_id}")
    
    # Пути
    external_dir = Path(args.external_dir)
    your_dataset_dir = Path('dataset_8classes')
    
    if not external_dir.exists():
        print(f"❌ Не найден внешний датасет: {external_dir}")
        return
    
    if not your_dataset_dir.exists():
        print(f"❌ Не найден dataset_8classes: {your_dataset_dir}")
        return
    
    # Выполняем merge
    merge_external_dataset(
        external_dir, 
        your_dataset_dir, 
        external_class_names,
        args.train_split,
        args.val_split
    )


if __name__ == '__main__':
    main()

