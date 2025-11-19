import { useState, useMemo, useCallback } from "react";
import { Button, Chip } from "@heroui/react";
import { motion } from "framer-motion";

const CLASS_NAMES_RU: Record<string, string> = {
  vibration_damper: "Виброгаситель",
  festoon_insulators: "Гирлянда изоляторов",
  traverse: "Траверса",
  bad_insulator: "Изолятор отсутствует",
  damaged_insulator: "Поврежденный изолятор",
  polymer_insulators: "Полимерные изоляторы",
};

interface DefectSummary {
  type: string;
  severity: string;
  description: string;
}

interface BboxSize {
  width: number;
  height: number;
  area: number;
  is_small: boolean;
}

interface Detection {
  class: string;
  class_ru: string;
  confidence: number;
  bbox: number[];
  bbox_size: BboxSize;
  defect_summary: DefectSummary;
}

interface Results {
  total_objects: number;
  defects_count: number;
  has_defects: boolean;
  statistics: Record<string, number>;
  detections: Detection[];
}

interface AnalysisHistoryContentsProps {
  results: Results;
  processedFilesCount: number;
  resultsArchiveFileId: string | null;
  onBack?: () => void;
}

export default function AnalysisHistoryContents({
  results,
  processedFilesCount,
  resultsArchiveFileId,
  onBack,
}: AnalysisHistoryContentsProps) {
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);

  const allClasses = results?.detections
    ? [...new Set(results.detections.map((d: Detection) => d.class))]
    : [];

  const isDefect = useCallback((className: string) => {
    return ["bad_insulator", "damaged_insulator"].includes(className);
  }, []);

  const filteredDetections = useMemo(() => {
    if (!results.detections) return [];
    if (selectedClasses.length === 0) return results.detections;
    return results.detections.filter((d: Detection) =>
      selectedClasses.includes(d.class)
    );
  }, [results.detections, selectedClasses]);

  const downloadResultsArchive = useCallback(async () => {
    if (!resultsArchiveFileId) return;

    try {
      const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
      const response = await fetch(
        `${BFF_SERVICE_URL}/files/${resultsArchiveFileId}/download`,
        {
          method: 'GET',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis_results_${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading archive:', error);
      alert('Не удалось скачать архив с результатами');
    }
  }, [resultsArchiveFileId]);

  return (
    <motion.div
      key="results"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="w-full h-full flex flex-col gap-6"
      style={{ padding: '128px 96px' }}
    >
      {/* Результаты */}
      <div className="space-y-8">
          {/* Статистика */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="relative text-center p-6 rounded-xl bg-white/5 overflow-hidden border border-white/10">
              <img
                src="/images/folder-light.svg"
                alt="folder-light"
                className="absolute bottom-14 left-0 w-full h-full object-cover"
              />
              <div className="relative z-10">
                <img
                  src="/images/folder.svg"
                  alt="folder"
                  className="mx-auto mb-3 drop-shadow-lg shadow-black/50"
                />
                 <div className="flex flex-col items-start">
                   <div className="text-[56px] font-extrabold text-white">
                     {processedFilesCount}
                   </div>
                   <h4 className="text-[16px] font-bold text-white/60 mb-3">
                     Обработано файлов
                   </h4>
                 </div>
              </div>
            </div>
            <div className="relative text-center p-6 rounded-xl bg-white/5 overflow-hidden border border-white/10">
              <img
                src="/images/illsuttration-2-light.svg"
                alt="illustration-1"
                className="absolute pointer-events-none opacity-75"
                style={{
                  top: '-15%',
                  right: '-20%',
                  width: '120%',
                  height: '120%',
                  objectFit: 'cover',
                  objectPosition: 'top right',
                }}
              />

              <img
                src="/images/illsuttration-2-light-2.svg"
                alt="illustration-2"
                className="absolute pointer-events-none opacity-75"
                style={{
                  top: '-15%',
                  left: '-20%',
                  width: '120%',
                  height: '120%',
                  objectFit: 'cover',
                  objectPosition: 'top left',
                }}
              />

              <div className="relative z-10">
                <img
                  src="/images/illsuttration-2.svg"
                  alt="illustration-1"
                  className="mx-auto mb-3 drop-shadow-lg shadow-black/50"
                />

                <div className="flex flex-col items-start">
                  <div className="text-[56px] font-extrabold text-white">
                  {results.total_objects}
                  </div>
                  <h4 className="text-[16px] font-bold text-white/60 mb-3">
                  Всего объектов
                  </h4>
                </div>
              </div>
            </div>
            <div className="relative text-center pb-6 pl-6 pr-6 rounded-xl bg-white/5 overflow-hidden border border-white/10">
              <img
                src="/images/danger-light.svg"
                alt="danger-light"
                className="absolute pointer-events-none opacity-75"
                style={{
                  width: '120%',
                  marginLeft: '-6%',
                  objectFit: 'cover',
                  objectPosition: 'top right',
                }}
              />
              <div className="relative z-10">
                <img
                  src="/images/danger.svg"
                  alt="danger"
                  className="mx-auto drop-shadow-lg shadow-black/50"
                />
                <div className="flex flex-col items-start" style={{ marginTop: '-5px' }}>
                  <div className="text-[56px] font-extrabold text-white">
                  {results.defects_count}
                  </div>
                  <h4 className="text-[16px] font-bold text-white/60 mb-3">
                  Дефектов
                  </h4>
                </div>
              </div>
            </div>
            <div className="text-center p-6 rounded-xl bg-white/5 border border-white/10">

              <div className="flex flex-col items-start">
                <div className="text-[56px] font-extrabold text-white">
                {results.total_objects - results.defects_count}
                </div>
                <h4 className="text-[16px] font-bold text-white/60 mb-3">
                  Без дефектов
                </h4>
              </div>
            </div>
          </div>

        {/* Кнопка скачивания архива */}
        {resultsArchiveFileId && (
          <div className="mt-8 flex justify-center">
            <Button
              size="lg"
              className="text-white font-bold text-lg rounded-full hover:scale-105 transition-all duration-300 flex items-center justify-center border border-white/60 h-[42px]"
              radius="full"
              style={{
                padding: '13px 24px',
                backgroundColor: 'rgba(88, 75, 255, 0.4)',
                fontWeight: 400
              }}
              onClick={downloadResultsArchive}
            >
              <svg
                className="w-5 h-5 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Скачать ZIP с результатами (boxed images)
            </Button>
          </div>
        )}

        {/* Детекции */}
        {results.detections && results.detections.length > 0 && (
          <div className="mt-8">
            <h3 className="text-2xl font-bold mb-6 text-white">
              🔍 Детекции
            </h3>

            <div className="mb-6">
              <label className="block mb-3 font-bold text-lg text-white/80">
                Фильтр по категориям:
              </label>
              <div className="flex flex-wrap gap-3">
                {allClasses.map((className) => (
                  <Chip
                    key={className}
                    variant={selectedClasses.includes(className) ? "solid" : "bordered"}
                    onClick={() => {
                      if (selectedClasses.includes(className)) {
                        setSelectedClasses(
                          selectedClasses.filter((c) => c !== className)
                        );
                      } else {
                        setSelectedClasses([...selectedClasses, className]);
                      }
                    }}
                    className="cursor-pointer text-base px-4 py-2 font-semibold transition-all border-white/30 text-white"
                    style={{
                      backgroundColor: selectedClasses.includes(className)
                        ? 'rgba(255, 255, 255, 0.2)'
                        : 'transparent'
                    }}
                  >
                    {CLASS_NAMES_RU[className] || className}
                  </Chip>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-white/20 bg-black/50">
              <table className="w-full border-collapse">
                <thead className="bg-white/5">
                  <tr>
                    <th className="text-left p-4 font-bold text-white text-sm">
                      Категория
                    </th>
                    <th className="text-left p-4 font-bold text-white text-sm">
                      Признак дефекта
                    </th>
                    <th className="text-left p-4 font-bold text-white text-sm">
                      Уверенность
                    </th>
                    <th className="text-left p-4 font-bold text-white text-sm">
                      Координаты
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDetections.map((detection, index) => (
                    <tr
                      key={index}
                      className="border-b border-white/10 hover:bg-white/5 transition-colors"
                    >
                      <td className="p-4">
                        <span className={`px-3 py-1 rounded text-sm font-semibold ${
                          isDefect(detection.class)
                            ? "bg-red-500/20 text-red-300"
                            : "bg-green-500/20 text-green-300"
                        }`}>
                          {detection.class_ru}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col gap-2">
                          <span className="text-white/80 font-semibold">
                            {detection.defect_summary?.type || "Норма"}
                          </span>
                          <p className="text-sm text-white/60">
                            {detection.defect_summary?.description ||
                              "Признаков дефекта не обнаружено"}
                          </p>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">
                            {(detection.confidence * 100).toFixed(1)}%
                          </span>
                          <div className="w-24 h-2 bg-white/20 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                detection.confidence > 0.7
                                  ? "bg-green-500"
                                  : detection.confidence > 0.5
                                  ? "bg-yellow-500"
                                  : "bg-red-500"
                              }`}
                              style={{ width: `${detection.confidence * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-white/60 font-mono bg-white/5 rounded">
                        [{detection.bbox.map((c) => Math.round(c)).join(", ")}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Кнопка возврата */}
        {onBack && (
          <div className="mt-8 text-center">
            <Button
              variant="bordered"
              className="border-white/30 text-white font-medium px-6 py-3 rounded-lg hover:bg-white/10"
              onClick={onBack}
            >
              Загрузить новые изображения
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

