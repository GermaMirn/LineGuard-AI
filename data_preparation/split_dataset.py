"""
Разделение датасета на train/val/test (80/10/10)
"""
import os
import shutil
from pathlib import Path
from sklearn.model_selection import train_test_split
import random

def split_dataset(dataset_dir, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, random_seed=42):
    """
    Разделение датасета на train/val/test

    Args:
        dataset_dir: директория с dataset/images и dataset/labels
        train_ratio: доля обучающей выборки
        val_ratio: доля валидационной выборки
        test_ratio: доля тестовой выборки
        random_seed: seed для воспроизводимости
    """
    random.seed(random_seed)

    images_dir = Path(dataset_dir) / "images"
    labels_dir = Path(dataset_dir) / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        print("❌ Ошибка: директории images/ или labels/ не найдены!")
        print("   Сначала запустите convert_coco_to_yolo.py")
        return

    # Очистка старых train/val/test папок
    print("🧹 Очистка старых train/val/test папок...")
    for split in ['train', 'val', 'test']:
        split_img_dir = images_dir / split
        split_label_dir = labels_dir / split

        if split_img_dir.exists():
            shutil.rmtree(split_img_dir)
            print(f"   Удалено: {split_img_dir}")
        if split_label_dir.exists():
            shutil.rmtree(split_label_dir)
            print(f"   Удалено: {split_label_dir}")

    # Получаем список всех изображений с аннотациями (рекурсивно во всех подпапках)
    image_files = []

    # Ищем все изображения рекурсивно
    for img_file in images_dir.rglob("*"):
        if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            # Получаем относительный путь от images_dir
            rel_path = img_file.relative_to(images_dir)
            # Сохраняем путь как строку (может быть с подпапками)
            image_stem = str(rel_path.with_suffix(''))

            # Ищем соответствующий label файл
            label_file = labels_dir / (image_stem + '.txt')
            if label_file.exists():
                image_files.append(image_stem)

    print(f"Всего изображений с аннотациями: {len(image_files)}")

    # Разделяем на train и temp (val + test)
    train_files, temp_files = train_test_split(
        image_files,
        test_size=(1 - train_ratio),
        random_state=random_seed
    )

    # Разделяем temp на val и test
    val_size = val_ratio / (val_ratio + test_ratio)
    val_files, test_files = train_test_split(
        temp_files,
        test_size=(1 - val_size),
        random_state=random_seed
    )

    print(f"\nРазделение:")
    print(f"  Train: {len(train_files)} ({len(train_files)/len(image_files)*100:.1f}%)")
    print(f"  Val:   {len(val_files)} ({len(val_files)/len(image_files)*100:.1f}%)")
    print(f"  Test:  {len(test_files)} ({len(test_files)/len(image_files)*100:.1f}%)")

    # Создаем структуру директорий (уже очищены выше)
    print("\n📁 Создание новых директорий...")
    for split in ['train', 'val', 'test']:
        split_img_dir = images_dir / split
        split_label_dir = labels_dir / split

        # Создаем новые директории
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_label_dir.mkdir(parents=True, exist_ok=True)

    print("✅ Директории созданы")

    # Копируем файлы
    splits = {
        'train': train_files,
        'val': val_files,
        'test': test_files
    }

    for split_name, files in splits.items():
        print(f"\nКопирование {split_name}...")
        copied_count = 0
        for file_stem in files:
            # file_stem может быть с подпапками (например, "BAD INSULATOR DETECTION.V11I.COCO/file")
            # Копируем изображение
            img_found = False
            for ext in ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
                img_src = images_dir / (file_stem + ext)
                if img_src.exists():
                    # Сохраняем только имя файла (без подпапок) в train/val/test
                    img_dst = images_dir / split_name / img_src.name

                    try:
                        shutil.copy2(img_src, img_dst)
                        # Устанавливаем права на запись
                        os.chmod(img_dst, 0o644)
                        img_found = True
                        break
                    except (PermissionError, OSError) as e:
                        print(f"  ⚠️  Ошибка при копировании {img_src.name}: {e}")
                        break

            if not img_found:
                continue  # Пропускаем если изображение не найдено

            # Копируем аннотацию
            label_src = labels_dir / (file_stem + '.txt')
            if label_src.exists():
                # Сохраняем только имя файла (без подпапок) в train/val/test
                label_dst = labels_dir / split_name / (Path(file_stem).name + '.txt')

                try:
                    shutil.copy2(label_src, label_dst)
                    # Устанавливаем права на запись
                    os.chmod(label_dst, 0o644)
                except (PermissionError, OSError) as e:
                    print(f"  ⚠️  Ошибка при копировании аннотации {label_src.name}: {e}")
                    continue

                copied_count += 1

        print(f"  ✅ Скопировано {copied_count} файлов")

    print("\n✅ Разделение завершено!")
    print(f"   Структура: {dataset_dir}/images/{{train,val,test}}/")
    print(f"              {dataset_dir}/labels/{{train,val,test}}/")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    dataset_dir = project_root / "dataset"

    print("=" * 60)
    print("Разделение датасета на train/val/test")
    print("=" * 60)

    split_dataset(dataset_dir, random_seed=42)

