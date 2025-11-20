"""
Подготовка датасета для 8 классов:
- Изображения берём из real_dataset/
- Метки берём из dataset/labels/ (старый датасет)
- Создаём новую структуру dataset_8classes/
"""
import os
import shutil
from pathlib import Path
from collections import defaultdict
import random
from sklearn.model_selection import train_test_split

# Маппинг старых классов (6) в новые (8)
# TODO: Уточните маппинг классов
CLASS_MAPPING = {
    0: 0,  # vibration_damper -> vibration_damper
    1: 1,  # festoon_insulators -> festoon_insulators
    2: 2,  # traverse -> traverse
    3: 3,  # bad_insulator -> bad_insulator
    4: 4,  # damaged_insulator -> damaged_insulator
    5: 5,  # polymer_insulators -> polymer_insulators
    # Классы 6 и 7 будут добавлены вручную или через новую разметку
}

def get_image_extensions():
    """Все поддерживаемые расширения изображений"""
    return ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG', '.tiff', '.TIFF', '.bmp', '.BMP']

def find_matching_label(image_path, labels_dir):
    """
    Поиск соответствующего label файла для изображения
    
    Args:
        image_path: путь к изображению
        labels_dir: директория с метками из старого датасета
    
    Returns:
        Path к label файлу или None
    """
    image_name = image_path.stem  # Имя без расширения
    
    # Ищем рекурсивно во всех подпапках labels_dir
    for label_file in labels_dir.rglob(f"{image_name}.txt"):
        return label_file
    
    # Если не нашли точное совпадение, пробуем поиск по части имени
    # (на случай если имена немного отличаются)
    for label_file in labels_dir.rglob("*.txt"):
        if image_name.lower() in label_file.stem.lower():
            return label_file
    
    return None

def convert_label_classes(label_path, class_mapping):
    """
    Конвертация классов в label файле по маппингу
    
    Args:
        label_path: путь к label файлу
        class_mapping: словарь маппинга старых классов в новые
    
    Returns:
        Список строк с новыми метками
    """
    new_labels = []
    
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            
            old_class = int(parts[0])
            
            # Конвертируем класс если есть в маппинге
            if old_class in class_mapping:
                new_class = class_mapping[old_class]
                # Заменяем класс, остальное оставляем как есть
                new_line = f"{new_class} {' '.join(parts[1:])}\n"
                new_labels.append(new_line)
            # Если класса нет в маппинге, пропускаем (или можно оставить как есть)
    
    return new_labels

def prepare_dataset(real_dataset_dir, old_labels_dir, output_dir, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, random_seed=42):
    """
    Подготовка датасета для 8 классов
    
    Args:
        real_dataset_dir: директория с новыми изображениями (real_dataset/)
        old_labels_dir: директория с метками из старого датасета (dataset/labels/)
        output_dir: выходная директория (dataset_8classes/)
        train_ratio: доля обучающей выборки
        val_ratio: доля валидационной выборки
        test_ratio: доля тестовой выборки
        random_seed: seed для воспроизводимости
    """
    random.seed(random_seed)
    
    real_dataset_path = Path(real_dataset_dir)
    old_labels_path = Path(old_labels_dir)
    output_path = Path(output_dir)
    
    # Очистка старой выходной директории
    if output_path.exists():
        print("🧹 Очистка старой директории...")
        shutil.rmtree(output_path)
    
    # Создаём структуру директорий
    print("📁 Создание структуры директорий...")
    for split in ['train', 'val', 'test']:
        (output_path / 'images' / split).mkdir(parents=True, exist_ok=True)
        (output_path / 'labels' / split).mkdir(parents=True, exist_ok=True)
    
    # Собираем все изображения из real_dataset (включая подпапки)
    print("\n🔍 Сканирование изображений в real_dataset...")
    all_images = []
    extensions = get_image_extensions()
    
    for img_file in real_dataset_path.rglob("*"):
        if img_file.is_file() and img_file.suffix in extensions:
            all_images.append(img_file)
    
    print(f"   Найдено изображений: {len(all_images)}")
    
    # Фильтруем изображения, для которых есть метки
    print("\n🏷️  Поиск соответствующих меток...")
    images_with_labels = []
    images_without_labels = []
    
    for img_path in all_images:
        label_path = find_matching_label(img_path, old_labels_path)
        if label_path:
            images_with_labels.append((img_path, label_path))
        else:
            images_without_labels.append(img_path)
    
    print(f"   С метками: {len(images_with_labels)}")
    print(f"   Без меток: {len(images_without_labels)}")
    
    if len(images_with_labels) == 0:
        print("\n❌ ОШИБКА: Не найдено изображений с соответствующими метками!")
        print("   Проверьте, что имена файлов в real_dataset/ совпадают с именами в dataset/labels/")
        return
    
    # Разделяем на train/val/test
    print("\n📊 Разделение на train/val/test...")
    train_data, temp_data = train_test_split(
        images_with_labels,
        test_size=(1 - train_ratio),
        random_state=random_seed
    )
    
    val_size = val_ratio / (val_ratio + test_ratio)
    val_data, test_data = train_test_split(
        temp_data,
        test_size=(1 - val_size),
        random_state=random_seed
    )
    
    splits = {
        'train': train_data,
        'val': val_data,
        'test': test_data
    }
    
    print(f"   Train: {len(train_data)} ({len(train_data)/len(images_with_labels)*100:.1f}%)")
    print(f"   Val:   {len(val_data)} ({len(val_data)/len(images_with_labels)*100:.1f}%)")
    print(f"   Test:  {len(test_data)} ({len(test_data)/len(images_with_labels)*100:.1f}%)")
    
    # Копируем файлы и конвертируем метки
    print("\n📦 Копирование файлов и конвертация меток...")
    
    stats = {'total': 0, 'converted': 0, 'skipped': 0}
    
    for split_name, data in splits.items():
        print(f"\n   {split_name}:")
        for img_path, label_path in data:
            # Копируем изображение
            img_dst = output_path / 'images' / split_name / img_path.name
            shutil.copy2(img_path, img_dst)
            
            # Конвертируем и копируем метку
            new_labels = convert_label_classes(label_path, CLASS_MAPPING)
            
            if len(new_labels) > 0:
                label_dst = output_path / 'labels' / split_name / (img_path.stem + '.txt')
                with open(label_dst, 'w') as f:
                    f.writelines(new_labels)
                stats['converted'] += 1
            else:
                stats['skipped'] += 1
            
            stats['total'] += 1
        
        print(f"      Обработано: {len(data)} файлов")
    
    print(f"\n✅ Подготовка датасета завершена!")
    print(f"   Всего обработано: {stats['total']}")
    print(f"   Конвертировано меток: {stats['converted']}")
    print(f"   Пропущено (нет аннотаций): {stats['skipped']}")
    print(f"   Выходная директория: {output_path}")
    
    # Статистика по классам
    print("\n📈 Статистика по классам:")
    class_counts = defaultdict(int)
    
    for split_name in ['train', 'val', 'test']:
        label_dir = output_path / 'labels' / split_name
        for label_file in label_dir.glob('*.txt'):
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        class_counts[class_id] += 1
    
    for class_id in sorted(class_counts.keys()):
        print(f"   Класс {class_id}: {class_counts[class_id]} аннотаций")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    
    real_dataset_dir = project_root / "real_dataset"
    old_labels_dir = project_root / "dataset" / "labels"
    output_dir = project_root / "dataset_8classes"
    
    print("=" * 60)
    print("Подготовка датасета для 8 классов")
    print("=" * 60)
    print(f"Изображения: {real_dataset_dir}")
    print(f"Метки: {old_labels_dir}")
    print(f"Выход: {output_dir}")
    print("=" * 60)
    
    if not real_dataset_dir.exists():
        print(f"❌ Ошибка: директория {real_dataset_dir} не найдена!")
        exit(1)
    
    if not old_labels_dir.exists():
        print(f"❌ Ошибка: директория {old_labels_dir} не найдена!")
        exit(1)
    
    prepare_dataset(
        real_dataset_dir=real_dataset_dir,
        old_labels_dir=old_labels_dir,
        output_dir=output_dir,
        random_seed=42
    )

