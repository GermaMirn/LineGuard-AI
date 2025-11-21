"""
🎯 Детальные метрики модели YOLOv8 для 8 классов
Включает визуализацию и моковые метрики для расширенного датасета
"""

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from typing import Dict, List, Tuple
    import json

    # Настройка стиля для красивых графиков
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        try:
            plt.style.use('seaborn-darkgrid')
        except:
            plt.style.use('default')
    sns.set_palette("husl")

    HAS_VISUALIZATION = True
except ImportError as e:
    print(f"⚠️ Предупреждение: Не удалось импортировать библиотеки для визуализации: {e}")
    print("   Установите: pip install matplotlib seaborn pandas numpy")
    HAS_VISUALIZATION = False
    import json
    from typing import Dict

# 8 классов модели
CLASS_NAMES = {
    0: "vibration_damper",      # виброгаситель
    1: "festoon_insulators",    # гирлянда изоляторов (стекло)
    2: "traverse",              # траверса
    3: "bad_insulator",         # отсутствующий изолятор
    4: "damaged_insulator",     # поврежденный изолятор
    5: "polymer_insulators",    # полимерные изоляторы
    6: "nest",                  # гнездо на траверсах
    7: "safety_sign"            # табличка безопасности
}

CLASS_NAMES_RU = {
    "vibration_damper": "Виброгаситель",
    "festoon_insulators": "Гирлянда изоляторов",
    "traverse": "Траверса",
    "bad_insulator": "Отсутствующий изолятор",
    "damaged_insulator": "Поврежденный изолятор",
    "polymer_insulators": "Полимерные изоляторы",
    "nest": "Гнездо на траверсах",
    "safety_sign": "Табличка безопасности"
}

# Моковые метрики для расширенного датасета (на основе реальных данных)
MOCK_METRICS_EXTENDED = {
    "vibration_damper": {
        "precision": 0.92,
        "recall": 0.89,
        "mAP50": 0.91,
        "mAP50_95": 0.68,
        "f1_score": 0.90,
        "annotations": 12450,
        "predictions": 11820,
        "true_positives": 11080,
        "false_positives": 740,
        "false_negatives": 1370
    },
    "festoon_insulators": {
        "precision": 0.88,
        "recall": 0.85,
        "mAP50": 0.87,
        "mAP50_95": 0.65,
        "f1_score": 0.86,
        "annotations": 9870,
        "predictions": 9520,
        "true_positives": 8389,
        "false_positives": 1131,
        "false_negatives": 1481
    },
    "traverse": {
        "precision": 0.94,
        "recall": 0.91,
        "mAP50": 0.93,
        "mAP50_95": 0.71,
        "f1_score": 0.92,
        "annotations": 15230,
        "predictions": 14780,
        "true_positives": 13859,
        "false_positives": 921,
        "false_negatives": 1371
    },
    "bad_insulator": {
        "precision": 0.86,
        "recall": 0.83,
        "mAP50": 0.85,
        "mAP50_95": 0.62,
        "f1_score": 0.84,
        "annotations": 3397,  # Реальные данные из notebook
        "predictions": 3280,
        "true_positives": 2819,
        "false_positives": 461,
        "false_negatives": 578
    },
    "damaged_insulator": {
        "precision": 0.84,
        "recall": 0.81,
        "mAP50": 0.83,
        "mAP50_95": 0.60,
        "f1_score": 0.82,
        "annotations": 2063,  # Реальные данные из notebook
        "predictions": 1980,
        "true_positives": 1671,
        "false_positives": 309,
        "false_negatives": 392
    },
    "polymer_insulators": {
        "precision": 0.90,
        "recall": 0.87,
        "mAP50": 0.89,
        "mAP50_95": 0.67,
        "f1_score": 0.88,
        "annotations": 6540,
        "predictions": 6320,
        "true_positives": 5694,
        "false_positives": 626,
        "false_negatives": 846
    },
    "nest": {
        "precision": 0.79,
        "recall": 0.76,
        "mAP50": 0.78,
        "mAP50_95": 0.55,
        "f1_score": 0.77,
        "annotations": 261,  # Реальные данные из notebook
        "predictions": 245,
        "true_positives": 198,
        "false_positives": 47,
        "false_negatives": 63
    },
    "safety_sign": {
        "precision": 0.82,
        "recall": 0.79,
        "mAP50": 0.81,
        "mAP50_95": 0.58,
        "f1_score": 0.80,
        "annotations": 375,  # Реальные данные из notebook
        "predictions": 360,
        "true_positives": 296,
        "false_positives": 64,
        "false_negatives": 79
    }
}


def create_metrics_dataframe(metrics_dict: Dict):
    """Создает DataFrame из словаря метрик"""
    if not HAS_VISUALIZATION:
        # Возвращаем простой список словарей если pandas недоступен
        data = []
        for class_name, metrics in metrics_dict.items():
            row = {
                "Класс": CLASS_NAMES_RU.get(class_name, class_name),
                "Класс (EN)": class_name,
                "Precision": metrics["precision"],
                "Recall": metrics["recall"],
                "mAP@0.5": metrics["mAP50"],
                "mAP@0.5:0.95": metrics["mAP50_95"],
                "F1-Score": metrics["f1_score"],
                "Аннотаций": metrics["annotations"],
                "Предсказаний": metrics["predictions"],
                "TP": metrics["true_positives"],
                "FP": metrics["false_positives"],
                "FN": metrics["false_negatives"]
            }
            data.append(row)
        return data

    data = []
    for class_name, metrics in metrics_dict.items():
        row = {
            "Класс": CLASS_NAMES_RU.get(class_name, class_name),
            "Класс (EN)": class_name,
            "Precision": metrics["precision"],
            "Recall": metrics["recall"],
            "mAP@0.5": metrics["mAP50"],
            "mAP@0.5:0.95": metrics["mAP50_95"],
            "F1-Score": metrics["f1_score"],
            "Аннотаций": metrics["annotations"],
            "Предсказаний": metrics["predictions"],
            "TP": metrics["true_positives"],
            "FP": metrics["false_positives"],
            "FN": metrics["false_negatives"]
        }
        data.append(row)

    df = pd.DataFrame(data)
    return df


def plot_class_metrics_comparison(df, save_path: str = None):
    """Визуализация метрик по классам"""
    if not HAS_VISUALIZATION:
        print("⚠️ Визуализация недоступна. Установите matplotlib и seaborn.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('📊 Детальные метрики модели YOLOv8 по классам', fontsize=20, fontweight='bold')

    # 1. Precision, Recall, F1-Score
    ax1 = axes[0, 0]
    x = np.arange(len(df))
    width = 0.25
    ax1.bar(x - width, df['Precision'], width, label='Precision', alpha=0.8, color='#3498db')
    ax1.bar(x, df['Recall'], width, label='Recall', alpha=0.8, color='#2ecc71')
    ax1.bar(x + width, df['F1-Score'], width, label='F1-Score', alpha=0.8, color='#e74c3c')
    ax1.set_xlabel('Классы', fontsize=12)
    ax1.set_ylabel('Метрика', fontsize=12)
    ax1.set_title('Precision, Recall и F1-Score по классам', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['Класс'], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1])

    # 2. mAP метрики
    ax2 = axes[0, 1]
    x = np.arange(len(df))
    width = 0.35
    ax2.bar(x - width/2, df['mAP@0.5'], width, label='mAP@0.5', alpha=0.8, color='#9b59b6')
    ax2.bar(x + width/2, df['mAP@0.5:0.95'], width, label='mAP@0.5:0.95', alpha=0.8, color='#f39c12')
    ax2.set_xlabel('Классы', fontsize=12)
    ax2.set_ylabel('mAP', fontsize=12)
    ax2.set_title('mAP метрики по классам', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(df['Класс'], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1])

    # 3. Количество аннотаций и предсказаний
    ax3 = axes[1, 0]
    x = np.arange(len(df))
    width = 0.35
    ax3.bar(x - width/2, df['Аннотаций'], width, label='Аннотаций (GT)', alpha=0.8, color='#1abc9c')
    ax3.bar(x + width/2, df['Предсказаний'], width, label='Предсказаний', alpha=0.8, color='#e67e22')
    ax3.set_xlabel('Классы', fontsize=12)
    ax3.set_ylabel('Количество', fontsize=12)
    ax3.set_title('Количество аннотаций и предсказаний', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(df['Класс'], rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. TP, FP, FN
    ax4 = axes[1, 1]
    x = np.arange(len(df))
    width = 0.25
    ax4.bar(x - width, df['TP'], width, label='True Positives', alpha=0.8, color='#27ae60')
    ax4.bar(x, df['FP'], width, label='False Positives', alpha=0.8, color='#c0392b')
    ax4.bar(x + width, df['FN'], width, label='False Negatives', alpha=0.8, color='#d35400')
    ax4.set_xlabel('Классы', fontsize=12)
    ax4.set_ylabel('Количество', fontsize=12)
    ax4.set_title('TP, FP, FN по классам', fontsize=14, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(df['Класс'], rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ График сохранен: {save_path}")
    plt.show()


def plot_heatmap_metrics(df, save_path: str = None):
    """Тепловая карта метрик"""
    if not HAS_VISUALIZATION:
        print("⚠️ Визуализация недоступна. Установите matplotlib и seaborn.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))

    # 1. Тепловая карта основных метрик
    metrics_cols = ['Precision', 'Recall', 'mAP@0.5', 'mAP@0.5:0.95', 'F1-Score']
    heatmap_data = df.set_index('Класс')[metrics_cols].T

    sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='RdYlGn',
                vmin=0, vmax=1, cbar_kws={'label': 'Значение метрики'},
                ax=axes[0], linewidths=1, linecolor='white')
    axes[0].set_title('🔥 Тепловая карта метрик по классам', fontsize=16, fontweight='bold', pad=20)
    axes[0].set_xlabel('Классы', fontsize=12)
    axes[0].set_ylabel('Метрики', fontsize=12)

    # 2. Тепловая карта TP, FP, FN (нормализованная)
    confusion_cols = ['TP', 'FP', 'FN']
    confusion_data = df.set_index('Класс')[confusion_cols]
    # Нормализуем по строкам для лучшей визуализации
    confusion_data_norm = confusion_data.div(confusion_data.sum(axis=1), axis=0)

    sns.heatmap(confusion_data_norm.T, annot=True, fmt='.3f', cmap='YlOrRd',
                cbar_kws={'label': 'Доля'},
                ax=axes[1], linewidths=1, linecolor='white')
    axes[1].set_title('📈 Распределение TP/FP/FN (нормализованное)', fontsize=16, fontweight='bold', pad=20)
    axes[1].set_xlabel('Классы', fontsize=12)
    axes[1].set_ylabel('Тип предсказания', fontsize=12)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Тепловая карта сохранена: {save_path}")
    plt.show()


def plot_radar_chart(df, save_path: str = None):
    """Радарная диаграмма метрик для каждого класса"""
    if not HAS_VISUALIZATION:
        print("⚠️ Визуализация недоступна. Установите matplotlib и seaborn.")
        return

    metrics = ['Precision', 'Recall', 'mAP@0.5', 'mAP@0.5:0.95', 'F1-Score']
    num_classes = len(df)

    # Вычисляем углы для каждого метрики
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]  # Замыкаем круг

    fig, axes = plt.subplots(2, 4, figsize=(20, 10), subplot_kw=dict(projection='polar'))
    fig.suptitle('🎯 Радарные диаграммы метрик по классам', fontsize=20, fontweight='bold', y=1.02)

    axes = axes.flatten()

    for idx, row in df.iterrows():
        ax = axes[idx]
        values = [row[m] for m in metrics]
        values += values[:1]  # Замыкаем круг

        ax.plot(angles, values, 'o-', linewidth=2, label=row['Класс'], color=f'C{idx}')
        ax.fill(angles, values, alpha=0.25, color=f'C{idx}')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics, fontsize=9)
        ax.set_ylim([0, 1])
        ax.set_title(row['Класс'], fontsize=11, fontweight='bold', pad=10)
        ax.grid(True)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Радарная диаграмма сохранена: {save_path}")
    plt.show()


def print_summary_statistics(df):
    """Выводит сводную статистику по метрикам"""
    print("\n" + "="*80)
    print("📊 СВОДНАЯ СТАТИСТИКА ПО МОДЕЛИ")
    print("="*80)

    # Поддержка как DataFrame, так и списка словарей
    if HAS_VISUALIZATION and isinstance(df, pd.DataFrame):
        print(f"\n🎯 Общие метрики:")
        print(f"   Средний Precision: {df['Precision'].mean():.4f} ± {df['Precision'].std():.4f}")
        print(f"   Средний Recall: {df['Recall'].mean():.4f} ± {df['Recall'].std():.4f}")
        print(f"   Средний mAP@0.5: {df['mAP@0.5'].mean():.4f} ± {df['mAP@0.5'].std():.4f}")
        print(f"   Средний mAP@0.5:0.95: {df['mAP@0.5:0.95'].mean():.4f} ± {df['mAP@0.5:0.95'].std():.4f}")
        print(f"   Средний F1-Score: {df['F1-Score'].mean():.4f} ± {df['F1-Score'].std():.4f}")

        print(f"\n📈 Лучшие классы:")
        best_precision = df.loc[df['Precision'].idxmax()]
        best_recall = df.loc[df['Recall'].idxmax()]
        best_map50 = df.loc[df['mAP@0.5'].idxmax()]
        print(f"   Лучший Precision: {best_precision['Класс']} ({best_precision['Precision']:.4f})")
        print(f"   Лучший Recall: {best_recall['Класс']} ({best_recall['Recall']:.4f})")
        print(f"   Лучший mAP@0.5: {best_map50['Класс']} ({best_map50['mAP@0.5']:.4f})")

        print(f"\n⚠️ Классы требующие внимания:")
        worst_precision = df.loc[df['Precision'].idxmin()]
        worst_recall = df.loc[df['Recall'].idxmin()]
        worst_map50 = df.loc[df['mAP@0.5'].idxmin()]
        print(f"   Низкий Precision: {worst_precision['Класс']} ({worst_precision['Precision']:.4f})")
        print(f"   Низкий Recall: {worst_recall['Класс']} ({worst_recall['Recall']:.4f})")
        print(f"   Низкий mAP@0.5: {worst_map50['Класс']} ({worst_map50['mAP@0.5']:.4f})")

        print(f"\n📦 Статистика по датасету:")
        print(f"   Всего аннотаций: {df['Аннотаций'].sum():,}")
        print(f"   Всего предсказаний: {df['Предсказаний'].sum():,}")
        print(f"   True Positives: {df['TP'].sum():,}")
        print(f"   False Positives: {df['FP'].sum():,}")
        print(f"   False Negatives: {df['FN'].sum():,}")

        total_precision = df['TP'].sum() / (df['TP'].sum() + df['FP'].sum()) if (df['TP'].sum() + df['FP'].sum()) > 0 else 0
        total_recall = df['TP'].sum() / (df['TP'].sum() + df['FN'].sum()) if (df['TP'].sum() + df['FN'].sum()) > 0 else 0
        print(f"\n🎯 Общая точность модели:")
        print(f"   Macro Precision: {df['Precision'].mean():.4f}")
        print(f"   Macro Recall: {df['Recall'].mean():.4f}")
        print(f"   Micro Precision: {total_precision:.4f}")
        print(f"   Micro Recall: {total_recall:.4f}")
    else:
        # Для списка словарей
        precisions = [row['Precision'] for row in df]
        recalls = [row['Recall'] for row in df]
        maps50 = [row['mAP@0.5'] for row in df]
        maps50_95 = [row['mAP@0.5:0.95'] for row in df]
        f1_scores = [row['F1-Score'] for row in df]

        def mean_std(values):
            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_val = variance ** 0.5
            return mean_val, std_val

        prec_mean, prec_std = mean_std(precisions)
        rec_mean, rec_std = mean_std(recalls)
        map50_mean, map50_std = mean_std(maps50)
        map50_95_mean, map50_95_std = mean_std(maps50_95)
        f1_mean, f1_std = mean_std(f1_scores)

        print(f"\n🎯 Общие метрики:")
        print(f"   Средний Precision: {prec_mean:.4f} ± {prec_std:.4f}")
        print(f"   Средний Recall: {rec_mean:.4f} ± {rec_std:.4f}")
        print(f"   Средний mAP@0.5: {map50_mean:.4f} ± {map50_std:.4f}")
        print(f"   Средний mAP@0.5:0.95: {map50_95_mean:.4f} ± {map50_95_std:.4f}")
        print(f"   Средний F1-Score: {f1_mean:.4f} ± {f1_std:.4f}")

        best_prec_idx = max(range(len(df)), key=lambda i: df[i]['Precision'])
        best_rec_idx = max(range(len(df)), key=lambda i: df[i]['Recall'])
        best_map50_idx = max(range(len(df)), key=lambda i: df[i]['mAP@0.5'])

        print(f"\n📈 Лучшие классы:")
        print(f"   Лучший Precision: {df[best_prec_idx]['Класс']} ({df[best_prec_idx]['Precision']:.4f})")
        print(f"   Лучший Recall: {df[best_rec_idx]['Класс']} ({df[best_rec_idx]['Recall']:.4f})")
        print(f"   Лучший mAP@0.5: {df[best_map50_idx]['Класс']} ({df[best_map50_idx]['mAP@0.5']:.4f})")

        total_annotations = sum(row['Аннотаций'] for row in df)
        total_predictions = sum(row['Предсказаний'] for row in df)
        total_tp = sum(row['TP'] for row in df)
        total_fp = sum(row['FP'] for row in df)
        total_fn = sum(row['FN'] for row in df)

        print(f"\n📦 Статистика по датасету:")
        print(f"   Всего аннотаций: {total_annotations:,}")
        print(f"   Всего предсказаний: {total_predictions:,}")
        print(f"   True Positives: {total_tp:,}")
        print(f"   False Positives: {total_fp:,}")
        print(f"   False Negatives: {total_fn:,}")

    print("="*80 + "\n")


def save_metrics_to_json(metrics_dict: Dict, save_path: str):
    """Сохраняет метрики в JSON файл"""
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
    print(f"✅ Метрики сохранены в JSON: {save_path}")


def main():
    """Основная функция для генерации всех метрик и визуализаций"""
    print("🚀 Генерация детальных метрик модели YOLOv8 для 8 классов\n")

    # Создаем DataFrame из моковых метрик
    df = create_metrics_dataframe(MOCK_METRICS_EXTENDED)

    # Выводим таблицу метрик
    print("📋 Таблица метрик по классам:")
    if HAS_VISUALIZATION and isinstance(df, pd.DataFrame):
        print(df.to_string(index=False))
    else:
        # Простой вывод для списка словарей
        print(f"{'Класс':<25} {'Precision':<10} {'Recall':<10} {'mAP@0.5':<10} {'F1-Score':<10}")
        print("-" * 70)
        for row in df:
            print(f"{row['Класс']:<25} {row['Precision']:<10.3f} {row['Recall']:<10.3f} {row['mAP@0.5']:<10.3f} {row['F1-Score']:<10.3f}")
    print("\n")

    # Выводим сводную статистику
    print_summary_statistics(df)

    # Создаем визуализации
    print("📊 Создание визуализаций...\n")

    # 1. Сравнение метрик по классам
    plot_class_metrics_comparison(df, save_path='metrics_comparison.png')

    # 2. Тепловые карты
    plot_heatmap_metrics(df, save_path='metrics_heatmap.png')

    # 3. Радарные диаграммы
    plot_radar_chart(df, save_path='metrics_radar.png')

    # Сохраняем метрики в JSON
    save_metrics_to_json(MOCK_METRICS_EXTENDED, 'model_metrics.json')

    # Сохраняем DataFrame в CSV
    if HAS_VISUALIZATION and isinstance(df, pd.DataFrame):
        df.to_csv('model_metrics.csv', index=False, encoding='utf-8')
        print("✅ Метрики сохранены в CSV: model_metrics.csv")
    else:
        # Сохраняем в CSV вручную
        import csv
        with open('model_metrics.csv', 'w', encoding='utf-8', newline='') as f:
            if df:
                writer = csv.DictWriter(f, fieldnames=df[0].keys())
                writer.writeheader()
                writer.writerows(df)
        print("✅ Метрики сохранены в CSV: model_metrics.csv")

    print("\n✅ Все метрики и визуализации готовы!")


if __name__ == "__main__":
    main()

