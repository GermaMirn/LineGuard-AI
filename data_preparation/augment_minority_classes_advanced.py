#!/usr/bin/env python3
"""
АГРЕССИВНАЯ аугментация данных для классов с малым количеством примеров
Создаёт x8 больше обучающих примеров с разнообразными трансформациями
"""

import os
import random
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np

# Классы для аугментации
MINORITY_CLASSES = [6, 7]  # nest, safety_sign

# Количество копий для каждого изображения
AUGMENTATION_FACTOR = 5  # x5 больше данных!

# Настройки
ROTATION_RANGE = (-25, 25)  # Более агрессивный поворот
BRIGHTNESS_RANGE = (0.6, 1.4)  # 60%-140%
CONTRAST_RANGE = (0.7, 1.3)  # 70%-130%
SATURATION_RANGE = (0.7, 1.3)
HUE_SHIFT_RANGE = (-10, 10)
BLUR_KERNEL_RANGE = (3, 7)
NOISE_RANGE = (0, 15)
ZOOM_RANGE = (0.9, 1.1)  # Zoom in/out 90%-110%


def read_yolo_label(label_path: Path) -> List[Tuple[int, float, float, float, float]]:
    """Читает YOLO label файл"""
    if not label_path.exists():
        return []

    boxes = []
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                boxes.append((class_id, x_center, y_center, width, height))
    return boxes


def write_yolo_label(label_path: Path, boxes: List[Tuple[int, float, float, float, float]]):
    """Записывает YOLO label файл с клипингом координат"""
    with open(label_path, 'w') as f:
        for box in boxes:
            class_id, x_center, y_center, width, height = box
            # Клипинг до [0, 1]
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            width = max(0.0, min(1.0, width))
            height = max(0.0, min(1.0, height))
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def rotate_image_and_boxes(image: np.ndarray, boxes: List[Tuple], angle: float) -> Tuple[np.ndarray, List[Tuple]]:
    """Поворот изображения и bbox"""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    return rotated, boxes


def adjust_brightness_contrast(image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
    """Яркость и контраст"""
    img = cv2.convertScaleAbs(image, alpha=contrast, beta=0)
    img = cv2.convertScaleAbs(img, alpha=brightness, beta=0)
    return img


def adjust_hsv(image: np.ndarray, saturation: float, hue_shift: int) -> np.ndarray:
    """Изменение HSV (насыщенность и оттенок)"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)

    # Saturation
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)

    # Hue shift
    hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180

    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def add_blur(image: np.ndarray, kernel_size: int) -> np.ndarray:
    """Размытие"""
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def add_sharpen(image: np.ndarray) -> np.ndarray:
    """Повышение резкости"""
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    return cv2.filter2D(image, -1, kernel)


def add_noise(image: np.ndarray, noise_level: float) -> np.ndarray:
    """Гауссов шум"""
    if noise_level == 0:
        return image

    noise = np.random.normal(0, noise_level, image.shape).astype(np.int16)
    noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def apply_clahe(image: np.ndarray) -> np.ndarray:
    """CLAHE - улучшение локального контраста"""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def zoom_image_and_boxes(image: np.ndarray, boxes: List[Tuple], zoom: float) -> Tuple[np.ndarray, List[Tuple]]:
    """Zoom in/out с корректировкой bbox"""
    h, w = image.shape[:2]

    if zoom == 1.0:
        return image, boxes

    # Вычисляем новый размер
    new_h = int(h / zoom)
    new_w = int(w / zoom)

    # Crop центр
    y1 = (h - new_h) // 2
    x1 = (w - new_w) // 2
    y2 = y1 + new_h
    x2 = x1 + new_w

    cropped = image[y1:y2, x1:x2]

    # Resize обратно к оригинальному размеру
    zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    # Bbox остаются относительно центра, поэтому не трогаем
    return zoomed, boxes


def flip_horizontal(image: np.ndarray, boxes: List[Tuple]) -> Tuple[np.ndarray, List[Tuple]]:
    """Горизонтальное отражение"""
    flipped_img = cv2.flip(image, 1)

    flipped_boxes = []
    for class_id, x_center, y_center, width, height in boxes:
        new_x_center = 1.0 - x_center
        flipped_boxes.append((class_id, new_x_center, y_center, width, height))

    return flipped_img, flipped_boxes


def flip_vertical(image: np.ndarray, boxes: List[Tuple]) -> Tuple[np.ndarray, List[Tuple]]:
    """Вертикальное отражение"""
    flipped_img = cv2.flip(image, 0)

    flipped_boxes = []
    for class_id, x_center, y_center, width, height in boxes:
        new_y_center = 1.0 - y_center
        flipped_boxes.append((class_id, x_center, new_y_center, width, height))

    return flipped_img, flipped_boxes


def add_shadow(image: np.ndarray) -> np.ndarray:
    """Добавляет случайную тень"""
    h, w = image.shape[:2]

    # Случайная тень
    top_y = random.randint(0, h // 2)
    bottom_y = random.randint(h // 2, h)

    shadow_mask = np.zeros((h, w), dtype=np.float32)
    shadow_mask[top_y:bottom_y, :] = random.uniform(0.4, 0.7)

    shadow_mask = cv2.GaussianBlur(shadow_mask, (51, 51), 0)

    shadowed = image.copy().astype(np.float32)
    shadowed = shadowed * (1 - shadow_mask[:, :, np.newaxis])

    return np.clip(shadowed, 0, 255).astype(np.uint8)


def augment_image(image_path: Path, label_path: Path, output_image_path: Path, output_label_path: Path, aug_id: int):
    """Применяет агрессивную аугментацию"""
    # Читаем
    image = cv2.imread(str(image_path))
    if image is None:
        return False

    boxes = read_yolo_label(label_path)
    if not boxes:
        return False

    augmented_img = image.copy()
    augmented_boxes = boxes.copy()

    # === НАБОР ТРАНСФОРМАЦИЙ (рандомный выбор) ===

    # 1. Поворот (70% вероятность)
    if random.random() > 0.3:
        angle = random.uniform(*ROTATION_RANGE)
        augmented_img, augmented_boxes = rotate_image_and_boxes(augmented_img, augmented_boxes, angle)

    # 2. Flip горизонтальный (50%)
    if random.random() > 0.5:
        augmented_img, augmented_boxes = flip_horizontal(augmented_img, augmented_boxes)

    # 3. Flip вертикальный (20%)
    if random.random() > 0.8:
        augmented_img, augmented_boxes = flip_vertical(augmented_img, augmented_boxes)

    # 4. Яркость и контраст (всегда)
    brightness = random.uniform(*BRIGHTNESS_RANGE)
    contrast = random.uniform(*CONTRAST_RANGE)
    augmented_img = adjust_brightness_contrast(augmented_img, brightness, contrast)

    # 5. HSV (70%)
    if random.random() > 0.3:
        saturation = random.uniform(*SATURATION_RANGE)
        hue_shift = random.randint(*HUE_SHIFT_RANGE)
        augmented_img = adjust_hsv(augmented_img, saturation, hue_shift)

    # 6. Blur ИЛИ Sharpen (50%)
    if random.random() > 0.5:
        if random.random() > 0.5:
            kernel_size = random.choice([3, 5, 7])
            augmented_img = add_blur(augmented_img, kernel_size)
        else:
            augmented_img = add_sharpen(augmented_img)

    # 7. Noise (30%)
    if random.random() > 0.7:
        noise_level = random.uniform(*NOISE_RANGE)
        augmented_img = add_noise(augmented_img, noise_level)

    # 8. CLAHE (40%)
    if random.random() > 0.6:
        augmented_img = apply_clahe(augmented_img)

    # 9. Zoom (30%)
    if random.random() > 0.7:
        zoom = random.uniform(*ZOOM_RANGE)
        augmented_img, augmented_boxes = zoom_image_and_boxes(augmented_img, augmented_boxes, zoom)

    # 10. Shadow (20%)
    if random.random() > 0.8:
        augmented_img = add_shadow(augmented_img)

    # Сохраняем
    cv2.imwrite(str(output_image_path), augmented_img)
    write_yolo_label(output_label_path, augmented_boxes)

    return True


def main():
    dataset_dir = Path(__file__).parent.parent / 'dataset_8classes'

    if not dataset_dir.exists():
        print(f"❌ Датасет не найден: {dataset_dir}")
        return

    print("🚀 АГРЕССИВНАЯ АУГМЕНТАЦИЯ (x5 копий)...")
    print(f"   Классы: {MINORITY_CLASSES}")
    print()

    total_created = 0

    for split in ['train', 'val', 'test']:
        images_dir = dataset_dir / 'images' / split
        labels_dir = dataset_dir / 'labels' / split

        if not images_dir.exists() or not labels_dir.exists():
            continue

        print(f"📂 {split}...")

        # Находим изображения с классами 6, 7
        images_to_augment = []

        for label_file in labels_dir.glob('*.txt'):
            boxes = read_yolo_label(label_file)
            has_minority = any(class_id in MINORITY_CLASSES for class_id, _, _, _, _ in boxes)

            if has_minority:
                image_name = label_file.stem
                for ext in ['.jpg', '.JPG', '.jpeg', '.png']:
                    image_path = images_dir / f"{image_name}{ext}"
                    if image_path.exists():
                        images_to_augment.append((image_path, label_file))
                        break

        print(f"   Найдено: {len(images_to_augment)}")

        if not images_to_augment:
            continue

        # Аугментация
        augmented_count = 0

        for image_path, label_path in images_to_augment:
            base_name = image_path.stem
            ext = image_path.suffix

            for i in range(AUGMENTATION_FACTOR):
                aug_name = f"{base_name}_adv{i}"
                output_image = images_dir / f"{aug_name}{ext}"
                output_label = labels_dir / f"{aug_name}.txt"

                if augment_image(image_path, label_path, output_image, output_label, i):
                    augmented_count += 1

                    if augmented_count % 100 == 0:
                        print(f"   ✅ {augmented_count}")

        print(f"   ✅ Создано: {augmented_count}\n")
        total_created += augmented_count

    print(f"🎉 ГОТОВО! Создано {total_created} изображений!")
    print(f"\n📊 Трансформации:")
    print(f"   • Поворот: ±25°")
    print(f"   • Flip: горизонтальный + вертикальный")
    print(f"   • Яркость: 60%-140%")
    print(f"   • Контраст: 70%-130%")
    print(f"   • HSV: насыщенность + оттенок")
    print(f"   • Blur/Sharpen")
    print(f"   • Noise: гауссов шум")
    print(f"   • CLAHE: улучшение контраста")
    print(f"   • Zoom: 90%-110%")
    print(f"   • Shadow: случайные тени")


if __name__ == '__main__':
    main()

