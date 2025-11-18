"""
Конвертация COCO формата аннотаций в YOLO формат для обучения YOLOv8
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from PIL import Image
import shutil

# 6 основных категорий по ТЗ
TARGET_CATEGORIES = {
    'vibration_damper': 0,
    'festoon_insulators': 1,
    'traverse': 2,
    'bad_insulator': 3,
    'damaged_insulator': 4,
    'polymer_insulators': 5
}

def convert_bbox_coco_to_yolo(bbox, img_width, img_height):
    """
    Конвертация bbox из COCO формата [x, y, width, height] в YOLO формат [center_x, center_y, width, height] (нормализованные)

    Args:
        bbox: [x, y, width, height] в пикселях
        img_width: ширина изображения
        img_height: высота изображения

    Returns:
        [center_x, center_y, width, height] нормализованные (0-1)
    """
    x, y, w, h = bbox

    # Центр bbox
    center_x = (x + w / 2) / img_width
    center_y = (y + h / 2) / img_height

    # Нормализованные размеры
    norm_w = w / img_width
    norm_h = h / img_height

    return [center_x, center_y, norm_w, norm_h]

def load_coco_annotations(coco_path):
    """Загрузка COCO аннотаций"""
    with open(coco_path, 'r', encoding='utf-8') as f:
        coco_data = json.load(f)
    return coco_data

def create_category_mapping(coco_data):
    """Создание маппинга category_id -> yolo_class_id для целевых категорий"""
    category_mapping = {}

    for cat in coco_data['categories']:
        cat_name = cat['name']
        if cat_name in TARGET_CATEGORIES:
            category_mapping[cat['id']] = TARGET_CATEGORIES[cat_name]
            print(f"Категория '{cat_name}' (id={cat['id']}) -> YOLO class {TARGET_CATEGORIES[cat_name]}")

    return category_mapping

def find_image_path(image_filename, images_dir):
    """
    Поиск пути к изображению в различных подпапках

    Args:
        image_filename: может быть просто имя файла или путь с подпапкой (например, "folder/file.jpg")
        images_dir: корневая директория с изображениями
    """
    # Если в filename есть путь (например, "BAD INSULATOR DETECTION.V11I.COCO/file.jpg")
    if '/' in image_filename or '\\' in image_filename:
        # Пробуем путь как есть
        full_path = os.path.join(images_dir, image_filename)
        if os.path.exists(full_path):
            return full_path

        # Пробуем нормализовать путь (заменить обратные слеши)
        normalized = image_filename.replace('\\', '/')
        full_path = os.path.join(images_dir, normalized)
        if os.path.exists(full_path):
            return full_path

    # Если просто имя файла, ищем во всех подпапках
    # Сначала пробуем как есть
    for root, dirs, files in os.walk(images_dir):
        if image_filename in files:
            return os.path.join(root, image_filename)

    # Если не найдено, пробуем разные варианты расширений
    base_name = os.path.splitext(image_filename)[0]
    for ext in ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
        filename = base_name + ext
        for root, dirs, files in os.walk(images_dir):
            if filename in files:
                return os.path.join(root, filename)

    # Пробуем найти по части имени (на случай если расширение или часть имени отличается)
    base_name_only = os.path.basename(base_name)  # Берем только имя без пути
    for root, dirs, files in os.walk(images_dir):
        for file in files:
            # Проверяем, начинается ли имя файла с base_name
            if file.startswith(base_name_only) or base_name_only in file:
                return os.path.join(root, file)

    return None

def convert_coco_to_yolo(coco_path, images_dir, output_dir):
    """
    Конвертация COCO датасета в YOLO формат

    Args:
        coco_path: путь к COCO JSON файлу
        images_dir: директория с изображениями
        output_dir: директория для вывода (dataset/images и dataset/labels)
    """
    # Очистка старых данных
    output_images_dir = Path(output_dir) / "images"
    output_labels_dir = Path(output_dir) / "labels"

    print("🧹 Очистка старых данных...")
    if output_images_dir.exists():
        shutil.rmtree(output_images_dir)
        print(f"   Удалено: {output_images_dir}")
    if output_labels_dir.exists():
        shutil.rmtree(output_labels_dir)
        print(f"   Удалено: {output_labels_dir}")

    print("Загрузка COCO аннотаций...")
    coco_data = load_coco_annotations(coco_path)

    print(f"Всего изображений: {len(coco_data['images'])}")
    print(f"Всего аннотаций: {len(coco_data['annotations'])}")
    print(f"Всего категорий: {len(coco_data['categories'])}")

    # Создаем маппинг категорий
    category_mapping = create_category_mapping(coco_data)
    print(f"\nЦелевых категорий для конвертации: {len(category_mapping)}")

    # Создаем выходные директории (уже очищены выше)
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)
    print("✅ Созданы новые директории")

    # Группируем аннотации по изображениям
    annotations_by_image = defaultdict(list)
    for ann in coco_data['annotations']:
        if ann['category_id'] in category_mapping:
            annotations_by_image[ann['image_id']].append(ann)

    # Создаем словарь изображений для быстрого доступа
    images_dict = {img['id']: img for img in coco_data['images']}

    # Статистика
    processed_images = 0
    skipped_images = 0
    total_annotations = 0

    print("\nКонвертация...")
    for image_id, image_info in images_dict.items():
        image_filename = image_info['file_name']

        # Ищем путь к изображению
        image_path = find_image_path(image_filename, images_dir)
        if image_path is None:
            print(f"⚠️  Изображение не найдено: {image_filename}")
            skipped_images += 1
            continue

        # Получаем размеры изображения
        try:
            with Image.open(image_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            print(f"⚠️  Ошибка при открытии {image_path}: {e}")
            skipped_images += 1
            continue

        # Получаем аннотации для этого изображения
        annotations = annotations_by_image.get(image_id, [])

        if len(annotations) == 0:
            # Пропускаем изображения без аннотаций целевых категорий
            skipped_images += 1
            continue

        # Копируем изображение
        # Если в image_filename есть подпапка, нужно создать её в выходной директории
        output_image_path = output_images_dir / image_filename

        # Создаем родительские директории, если их нет
        output_image_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(image_path, output_image_path)

        # Создаем YOLO аннотацию
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = output_labels_dir / label_filename

        # Создаем родительские директории для label, если их нет
        label_path.parent.mkdir(parents=True, exist_ok=True)

        with open(label_path, 'w') as f:
            for ann in annotations:
                yolo_class = category_mapping[ann['category_id']]
                bbox_yolo = convert_bbox_coco_to_yolo(
                    ann['bbox'],
                    img_width,
                    img_height
                )

                # Записываем в YOLO формате: class_id center_x center_y width height
                f.write(f"{yolo_class} {bbox_yolo[0]:.6f} {bbox_yolo[1]:.6f} {bbox_yolo[2]:.6f} {bbox_yolo[3]:.6f}\n")

        processed_images += 1
        total_annotations += len(annotations)

        if processed_images % 100 == 0:
            print(f"Обработано изображений: {processed_images}")

    print(f"\n✅ Конвертация завершена!")
    print(f"   Обработано изображений: {processed_images}")
    print(f"   Пропущено изображений: {skipped_images}")
    print(f"   Всего аннотаций: {total_annotations}")
    print(f"   Изображения сохранены в: {output_images_dir}")
    print(f"   Аннотации сохранены в: {output_labels_dir}")

if __name__ == "__main__":
    # Пути (data_preparation теперь в корне проекта)
    project_root = Path(__file__).parent.parent
    # Проверяем оба возможных расположения датасета
    coco_path_1 = project_root / "data" / "insulators" / "annotation_data.json"
    coco_path_2 = project_root / "dataset" / "insulators" / "annotation_data.json"

    images_dir_1 = project_root / "data" / "insulators" / "images"
    images_dir_2 = project_root / "dataset" / "insulators" / "images"

    # Выбираем существующий путь
    if coco_path_2.exists():
        coco_path = coco_path_2
        images_dir = images_dir_2
        print("✅ Используется датасет из dataset/insulators/")
    elif coco_path_1.exists():
        coco_path = coco_path_1
        images_dir = images_dir_1
        print("✅ Используется датасет из data/insulators/")
    else:
        coco_path = None
        images_dir = None

    output_dir = project_root / "dataset"

    print("=" * 60)
    print("Конвертация COCO → YOLO формат")
    print("=" * 60)

    if coco_path is None or images_dir is None:
        print("❌ Ошибка: датасет не найден!")
        print("   Искал в:")
        print(f"   - {coco_path_1}")
        print(f"   - {coco_path_2}")
        exit(1)

    print(f"COCO файл: {coco_path}")
    print(f"Изображения: {images_dir}")
    print(f"Выходная директория: {output_dir}")
    print("=" * 60)

    if not coco_path.exists():
        print(f"❌ Ошибка: файл {coco_path} не найден!")
        exit(1)

    if not images_dir.exists():
        print(f"❌ Ошибка: директория {images_dir} не найдена!")
        exit(1)

    convert_coco_to_yolo(coco_path, images_dir, output_dir)

