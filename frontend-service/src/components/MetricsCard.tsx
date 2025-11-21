import { memo } from "react";
import { Card, CardBody } from "@heroui/react";
import { getDefectType, getDefectMetadata, getDefectTypeName } from "@/types/metrics";

interface Metric {
  detection_id?: string;
  class_name: string;
  class_name_ru?: string;
  confidence: number;
  bbox: number[];
  defect_type?: string;
  severity?: string;
  description?: string;
  is_manual?: boolean;
}

interface MetricsCardProps {
  metric: Metric;
  index: number;
}

const MetricsCard = memo(({ metric, index }: MetricsCardProps) => {
  // Определяем тип и severity дефекта
  const isDefect = metric.defect_type && 
                   metric.defect_type !== 'normal' &&
                   metric.severity !== 'none' &&
                   metric.severity !== null;

  const severity = metric.severity;

  // Используем систему метрик
  const metadata = getDefectMetadata(severity, Boolean(isDefect));
  const defectType = getDefectType(
    metric.class_name_ru || metric.class_name,
    metric.defect_type === 'damage' ? 'Повреждение' : 
    metric.defect_type === 'missing' ? 'Отсутствие' : 'Норма'
  );
  const defectTypeName = getDefectTypeName(defectType);

  const confidencePercent = (metric.confidence * 100).toFixed(0);

  return (
    <Card
      key={`metric-${index}`}
      className="flex-shrink-0"
      style={{
        backgroundColor: metadata.bgColor,
        minWidth: '320px',
        width: '320px',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      <CardBody className="flex flex-col gap-4 p-5">
        {/* Иконка и название */}
        <div className="flex items-center gap-4">
          {/* Иконка в кружке */}
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: metadata.iconBgColor }}
          >
            {isDefect ? (
              <svg className="w-6 h-6" fill={metadata.iconColor} viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke={metadata.iconColor} strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </div>
          {/* Название объекта */}
          <div className="flex-1 min-w-0">
            <h4 className="text-base font-semibold text-white truncate">
              {metric.class_name_ru || metric.class_name}
            </h4>
            {metric.is_manual && (
              <span className="text-xs text-white/50 italic">Ручная аннотация</span>
            )}
          </div>
        </div>

        {/* Прогресс бар уверенности */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-white/70 font-medium">Уверенность</span>
            <span className="text-white font-bold text-lg">{confidencePercent}%</span>
          </div>
          <div className="w-full h-2.5 bg-white/15 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${confidencePercent}%`,
                backgroundColor: '#10B981' // Зеленый цвет
              }}
            />
          </div>
        </div>

        {/* Тип повреждения */}
        {isDefect && defectTypeName && (
          <div>
            <p className="text-sm text-white/90">
              Тип повреждения: <span className="font-semibold">
                {defectTypeName}
              </span>
            </p>
            {metric.description && (
              <p className="text-xs text-white/70 mt-1">
                {metric.description}
              </p>
            )}
          </div>
        )}

        {/* Информация о ручной аннотации */}
        {metric.is_manual && (
          <div className="pt-2 border-t border-white/10">
            <p className="text-xs text-white/60 italic">
              ✏️ Ручная аннотация
            </p>
          </div>
        )}
      </CardBody>
    </Card>
  );
});

MetricsCard.displayName = 'MetricsCard';

export default MetricsCard;

