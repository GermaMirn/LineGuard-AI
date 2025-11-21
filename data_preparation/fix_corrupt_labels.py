#!/usr/bin/env python3
"""
Исправляет bbox координаты выходящие за границы [0, 1]
Обрезает координаты до диапазона [0.0, 1.0]
"""

from pathlib import Path

def fix_bbox_coordinates(label_path: Path) -> bool:
    """Исправляет координаты в YOLO label файле"""
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        fixed_lines = []
        was_fixed = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) < 5:
                fixed_lines.append(line + '\n')
                continue
            
            class_id = parts[0]
            
            try:
                coords = [float(x) for x in parts[1:5]]
            except ValueError:
                fixed_lines.append(line + '\n')
                continue
            
            # Обрезаем координаты до [0, 1]
            fixed_coords = [max(0.0, min(1.0, c)) for c in coords]
            
            if coords != fixed_coords:
                was_fixed = True
            
            # Пересобираем строку
            fixed_line = f"{class_id} {' '.join(f'{c:.6f}' for c in fixed_coords)}\n"
            fixed_lines.append(fixed_line)
        
        # Сохраняем исправленный файл
        if was_fixed:
            with open(label_path, 'w') as f:
                f.writelines(fixed_lines)
        
        return was_fixed
    
    except Exception as e:
        print(f"❌ Ошибка {label_path}: {e}")
        return False


def main():
    dataset_path = Path('dataset_8classes')
    
    if not dataset_path.exists():
        print(f"❌ Датасет не найден: {dataset_path}")
        return
    
    print("🔧 ИСПРАВЛЕНИЕ CORRUPT LABELS")
    print("="*60)
    
    total_fixed = 0
    total_labels = 0
    
    for split in ['train', 'val', 'test']:
        labels_dir = dataset_path / 'labels' / split
        if not labels_dir.exists():
            print(f"⚠️ Не найден: {labels_dir}")
            continue
        
        print(f"\n📂 Обработка {split}...")
        
        split_fixed = 0
        split_total = 0
        
        for label_file in labels_dir.glob('*.txt'):
            split_total += 1
            if fix_bbox_coordinates(label_file):
                split_fixed += 1
        
        total_labels += split_total
        total_fixed += split_fixed
        
        print(f"   Всего labels: {split_total}")
        print(f"   Исправлено: {split_fixed} ({100*split_fixed/split_total if split_total > 0 else 0:.1f}%)")
    
    print("\n" + "="*60)
    print(f"✅ ГОТОВО!")
    print(f"   Всего labels: {total_labels}")
    print(f"   Исправлено: {total_fixed} ({100*total_fixed/total_labels if total_labels > 0 else 0:.1f}%)")
    print("\n💡 Теперь пересоздайте архив:")
    print("   tar -czf dataset_8classes_fixed.tar.gz --no-xattrs dataset_8classes/")


if __name__ == '__main__':
    main()

