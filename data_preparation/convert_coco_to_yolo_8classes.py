"""
Конвертация COCO формата аннотаций в YOLO формат для 8 классов
Включает nest и safety_sign
"""
import json
import os
from pathlib import Path
from collections import defaultdict
import shutil

# 8 категорий (добавили nest и safety_sign)
TARGET_CATEGORIES = {
    'vibration_damper': 0,
    'festoon_insulators': 1,
    'traverse': 2,
    'bad_insulator': 3,
    'damaged_insulator': 4,
    'polymer_insulators': 5,
    'nest': 6,              # НОВЫЙ
    'safety_sign+': 7       # НОВЫЙ (в COCO называется safety_sign+)
}

def convert_bbox_coco_to_yolo(bbox, img_width, img_height):
    """Конвертация bbox из COCO в YOLO формат"""
    x, y, w, h = bbox
    center_x = (x + w / 2) / img_width
    center_y = (y + h / 2) / img_height
    norm_w = w / img_width
    norm_h = h / img_height
    return [center_x, center_y, norm_w, norm_h]

def load_coco_annotations(coco_path):
    """Загрузка COCO аннотаций"""
    with open(coco_path, 'r', encoding='utf-8') as f:
        coco_data = json.load(f)
    return coco_data

def create_category_mapping(coco_data):
    """Создание маппинга category_id -> yolo_class_id"""
    category_mapping = {}

    for cat in coco_data['categories']:
        cat_name = cat['name']
        if cat_name in TARGET_CATEGORIES:
            category_mapping[cat['id']] = TARGET_CATEGORIES[cat_name]
            print(f"Категория '{cat_name}' (id={cat['id']}) -> YOLO class {TARGET_CATEGORIES[cat_name]}")

    return category_mapping

def find_image_path(image_filename, images_dir):
    """Поиск пути к изображению"""
    if '/' in image_filename or '\\' in image_filename:
        full_path = os.path.join(images_dir, image_filename)
        if os.path.exists(full_path):
            return full_path

    for root, dirs, files in os.walk(images_dir):
        if image_filename in files:
            return os.path.join(root, image_filename)

    base_name = os.path.splitext(image_filename)[0]
    for ext in ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
        filename = base_name + ext
        for root, dirs, files in os.walk(images_dir):
            if filename in files:
                return os.path.join(root, filename)

    return None

def convert_coco_to_yolo_8classes(coco_path, images_dir, output_dir):
    """Конвертация COCO датасета в YOLO формат (8 классов)"""
    output_images_dir = Path(output_dir) / "images"
    output_labels_dir = Path(output_dir) / "labels"

    print("🧹 Очистка старых данных...")
    if output_images_dir.exists():
        shutil.rmtree(output_images_dir)
    if output_labels_dir.exists():
        shutil.rmtree(output_labels_dir)

    print("Загрузка COCO аннотаций...")
    coco_data = load_coco_annotations(coco_path)

    print(f"Всего изображений: {len(coco_data['images'])}")
    print(f"Всего аннотаций: {len(coco_data['annotations'])}")

    category_mapping = create_category_mapping(coco_data)
    print(f"\nЦелевых категорий: {len(category_mapping)}")

    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)

    annotations_by_image = defaultdict(list)
    for ann in coco_data['annotations']:
        if ann['category_id'] in category_mapping:
            annotations_by_image[ann['image_id']].append(ann)

    images_dict = {img['id']: img for img in coco_data['images']}

    processed_images = 0
    skipped_images = 0
    total_annotations = 0
    class_counts = defaultdict(int)

    print("\nКонвертация...")
    for image_id, image_info in images_dict.items():
        image_filename = image_info['file_name']
        image_path = find_image_path(image_filename, images_dir)

        if image_path is None:
            skipped_images += 1
            continue

        # Получаем размеры из COCO (если нет - используем дефолтные)
        img_width = image_info.get('width', 1920)
        img_height = image_info.get('height', 1080)

        annotations = annotations_by_image.get(image_id, [])

        if len(annotations) == 0:
            skipped_images += 1
            continue

        output_image_path = output_images_dir / image_filename
        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_image_path)

        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = output_labels_dir / label_filename
        label_path.parent.mkdir(parents=True, exist_ok=True)

        with open(label_path, 'w') as f:
            for ann in annotations:
                yolo_class = category_mapping[ann['category_id']]
                bbox_yolo = convert_bbox_coco_to_yolo(
                    ann['bbox'],
                    img_width,
                    img_height
                )
                f.write(f"{yolo_class} {bbox_yolo[0]:.6f} {bbox_yolo[1]:.6f} {bbox_yolo[2]:.6f} {bbox_yolo[3]:.6f}\n")
                class_counts[yolo_class] += 1

        processed_images += 1
        total_annotations += len(annotations)

        if processed_images % 100 == 0:
            print(f"Обработано изображений: {processed_images}")

    print(f"\n✅ Конвертация завершена!")
    print(f"   Обработано изображений: {processed_images}")
    print(f"   Пропущено изображений: {skipped_images}")
    print(f"   Всего аннотаций: {total_annotations}")

    print(f"\n📊 Статистика по классам:")
    for cls in sorted(class_counts.keys()):
        print(f"   Класс {cls}: {class_counts[cls]} аннотаций")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent

    coco_path = project_root / "dataset" / "insulators" / "annotation_data.json"
    images_dir = project_root / "dataset" / "insulators" / "images"
    output_dir = project_root / "dataset_temp_8classes"

    print("=" * 60)
    print("Конвертация COCO → YOLO (8 классов)")
    print("=" * 60)
    print(f"COCO файл: {coco_path}")
    print(f"Изображения: {images_dir}")
    print(f"Выход: {output_dir}")
    print("=" * 60)

    if not coco_path.exists():
        print(f"❌ Ошибка: файл {coco_path} не найден!")
        exit(1)

    if not images_dir.exists():
        print(f"❌ Ошибка: директория {images_dir} не найдена!")
        exit(1)

    convert_coco_to_yolo_8classes(coco_path, images_dir, output_dir)

