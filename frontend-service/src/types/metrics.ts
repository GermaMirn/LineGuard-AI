// Типы дефектов и их метаданные

export enum DefectType {
  DAMAGE = 'damage', // Повреждение (что-то сломано)
  MISSING = 'missing', // Отсутствие (чего-то не хватает)
  NORMAL = 'normal', // Норма
}

export enum Severity {
  CRITICAL = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  NONE = 'none',
}

export interface DefectMetadata {
  type: DefectType;
  displayName: string;
  color: string; // Цвет текста
  bgColor: string; // Цвет фона карточки
  iconBgColor: string; // Цвет фона иконки
  iconColor: string; // Цвет иконки
}

// Определяем тип дефекта по классу или описанию
export function getDefectType(className: string, defectSummaryType?: string): DefectType {
  const lowerClassName = className.toLowerCase();
  const lowerDefectType = defectSummaryType?.toLowerCase() || '';

  // Проверяем на отсутствие
  if (
    lowerClassName.includes('отсутств') ||
    lowerDefectType.includes('отсутств') ||
    lowerClassName.includes('missing')
  ) {
    return DefectType.MISSING;
  }

  // Проверяем на повреждение
  if (
    lowerDefectType.includes('повреж') ||
    lowerDefectType.includes('damage') ||
    lowerDefectType !== 'норма'
  ) {
    return DefectType.DAMAGE;
  }

  return DefectType.NORMAL;
}

// Получаем метаданные для карточки по severity
export function getDefectMetadata(
  severity: string | null | undefined,
  isDefect: boolean
): DefectMetadata {
  if (!isDefect || !severity || severity === 'none') {
    // Обычный объект без дефектов - СИНИЙ
    return {
      type: DefectType.NORMAL,
      displayName: '',
      color: '#FFFFFF',
      bgColor: 'rgba(55, 65, 81, 0.6)', // Темно-синий
      iconBgColor: 'rgba(255, 255, 255, 0.15)',
      iconColor: '#FFFFFF',
    };
  }

  // Любой дефект (повреждение или отсутствие) - КРАСНЫЙ
  const isCritical = severity === 'high' || severity === 'критическая';
  const isWarning = severity === 'medium' || severity === 'средняя';

  return {
    type: DefectType.DAMAGE,
    displayName: isCritical ? 'тяжелая' : isWarning ? 'средняя' : 'низкая',
    color: '#EF4444', // Красный текст
    bgColor: 'rgba(127, 29, 29, 0.8)', // Темно-красный фон
    iconBgColor: 'rgba(220, 38, 38, 0.4)',
    iconColor: '#EF4444',
  };
}

// Получаем название типа повреждения для отображения
export function getDefectTypeName(defectType: DefectType): string {
  switch (defectType) {
    case DefectType.MISSING:
      return 'отсутствует';
    case DefectType.DAMAGE:
      return 'повреждён';
    default:
      return '';
  }
}

