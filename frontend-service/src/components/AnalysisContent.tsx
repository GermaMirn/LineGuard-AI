import { useState, useRef, useEffect } from "react";
import { Button, Progress, Chip } from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
import apiClient from "@/shared/api/axios";

const CLASS_NAMES_RU: Record<string, string> = {
  vibration_damper: "Виброгаситель",
  festoon_insulators: "Гирлянда изоляторов",
  traverse: "Траверса",
  bad_insulator: "Изолятор отсутствует",
  damaged_insulator: "Поврежденный изолятор",
  polymer_insulators: "Полимерные изоляторы",
};

const DEFECT_CLASSES = ["bad_insulator", "damaged_insulator"];

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

export default function AnalysisContent() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.35);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const allClasses = results?.detections
    ? [...new Set(results.detections.map((d: Detection) => d.class))]
    : [];

  const filteredDetections = results?.detections
    ? selectedClasses.length === 0
      ? results.detections
      : results.detections.filter((d) => selectedClasses.includes(d.class))
    : [];

  useEffect(() => {
    if (results && imageRef.current && canvasRef.current) {
      drawBoundingBoxes();
    }
  }, [results, selectedClasses]);

  useEffect(() => {
    const handleResize = () => {
      if (results && imageRef.current && canvasRef.current) {
        setTimeout(() => {
          drawBoundingBoxes();
        }, 100);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [results]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      previewImage(file);
      setError(null);
      setResults(null);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      setSelectedFile(file);
      previewImage(file);
      setError(null);
      setResults(null);
    }
  };

  const previewImage = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const analyzeImage = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await apiClient.post(
        `/predict?conf=${confidenceThreshold}`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 60000,
        }
      );

      setResults(response.data as Results);
      const detections = (response.data as Results).detections || [];
      const newAllClasses = [...new Set(detections.map((d: Detection) => d.class))];
      setSelectedClasses(newAllClasses);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || "Ошибка при обработке изображения"
      );
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setImagePreview(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const isDefect = (className: string) => {
    return DEFECT_CLASSES.includes(className);
  };

  const drawBoundingBoxes = () => {
    if (!results || !results.detections || !canvasRef.current || !imageRef.current) {
      return;
    }

    const img = imageRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (!ctx || !img.complete) {
      return;
    }

    if (img.naturalWidth === 0 || img.naturalHeight === 0) {
      return;
    }

    const imgRect = img.getBoundingClientRect();
    const displayWidth = imgRect.width;
    const displayHeight = imgRect.height;

    canvas.width = displayWidth;
    canvas.height = displayHeight;
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;
    canvas.style.position = "absolute";
    canvas.style.top = "0px";
    canvas.style.left = "0px";

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = displayWidth / img.naturalWidth;
    const scaleY = displayHeight / img.naturalHeight;

    const colors: Record<string, string> = {
      vibration_damper: "#3B82F6",
      festoon_insulators: "#10B981",
      traverse: "#8B5CF6",
      bad_insulator: "#EF4444",
      damaged_insulator: "#F59E0B",
      polymer_insulators: "#06B6D4",
    };

    filteredDetections.forEach((detection) => {
      const [x1, y1, x2, y2] = detection.bbox;
      const defect = isDefect(detection.class);
      const color = colors[detection.class] || "#666666";

      const scaledX1 = x1 * scaleX;
      const scaledY1 = y1 * scaleY;
      const scaledX2 = x2 * scaleX;
      const scaledY2 = y2 * scaleY;
      const width = scaledX2 - scaledX1;
      const height = scaledY2 - scaledY1;

      ctx.strokeStyle = color;
      ctx.lineWidth = defect ? 4 : 3;
      ctx.setLineDash(defect ? [8, 4] : []);
      ctx.strokeRect(scaledX1, scaledY1, width, height);

      const label = defect
        ? `${detection.class_ru} · ${detection.defect_summary?.type || "дефект"}`
        : detection.class_ru;
      const text = `${label} ${(detection.confidence * 100).toFixed(0)}%`;
      ctx.font = "bold 16px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      const textMetrics = ctx.measureText(text);
      const textWidth = textMetrics.width;
      const textHeight = 24;
      const padding = 8;

      ctx.fillStyle = color;
      ctx.globalAlpha = 0.9;
      ctx.fillRect(
        scaledX1,
        Math.max(0, scaledY1 - textHeight),
        textWidth + padding * 2,
        textHeight
      );
      ctx.globalAlpha = 1.0;

      ctx.fillStyle = "white";
      ctx.fillText(
        text,
        scaledX1 + padding,
        Math.max(textHeight - 5, scaledY1 - 5)
      );

      if (defect) {
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.2;
        ctx.fillRect(scaledX1, scaledY1, width, height);
        ctx.globalAlpha = 1.0;
      }
    });
  };

  return (
    <div className="h-full flex items-center justify-center" style={{ padding: '128px 96px' }}>
      <AnimatePresence mode="wait">
        {!results ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="w-full h-full"
          >
            {/* Drop Zone */}
            <div
              className={`relative border-2 border-dashed rounded-2xl text-center cursor-pointer transition-all duration-300 w-full h-full flex items-center justify-center ${
                isDragging
                  ? "border-white bg-white/5 scale-[1.01]"
                  : "border-white/30 hover:border-white/50 hover:bg-white/5"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                accept="image/jpeg,image/jpg,image/png,image/tiff"
                className="hidden"
              />

              {!selectedFile ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center gap-[24px]"
                >
                  {/* Иконка папки с плюсом */}
                  <div className="relative">
                    <img
                      src="/images/new-folder.svg"
                      alt="new-folder"
                    />
                  </div>

                  <div className="flex flex-col items-center gap-[10px]">
                    {/* Заголовок */}
                    <h2 className="text-3xl font-bold text-white">
                      Загрузите данные
                    </h2>

                    {/* Описание */}
                    <p className="text-white/70 text-base max-w-md leading-tight w-[300px]">
                      Добавьте изображения или <br/>
                      кадры дрона, и LineGuard AI <br />
                      выполнит детальный анализ <br />
                      состояния электросетей
                    </p>
                  </div>

                  {/* Кнопка загрузки */}
                  <Button
                    className="bg-white text-black rounded-full whitespace-nowrap flex items-center justify-center gap-[4px]"
                    style={{ padding: '7px 16px 11px 16px', fontWeight: 550 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    <img src="/images/plus.svg" alt="plus" className="mr-2" />
                    <p className="text-base font-medium">
                      Загрузить данные
                    </p>
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center gap-4"
                >
                  <div className="text-6xl">✅</div>
                  <p className="text-xl font-semibold text-white">{selectedFile.name}</p>
                  <p className="text-white/60">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <div className="flex gap-4 mt-4">
                    <Button
                      className="bg-white text-black font-medium px-6 py-3 rounded-lg hover:bg-white/90"
                      onClick={(e) => {
                        e.stopPropagation();
                        analyzeImage();
                      }}
                      isLoading={loading}
                      disabled={loading}
                    >
                      {loading ? "Обработка..." : "Начать анализ"}
                    </Button>
                    <Button
                      variant="bordered"
                      className="border-white/30 text-white font-medium px-6 py-3 rounded-lg hover:bg-white/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        clearFile();
                      }}
                    >
                      Очистить
                    </Button>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Настройки (показываются только если файл выбран) */}
            {selectedFile && !loading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-6 bg-white/5 rounded-xl border border-white/10"
              >
                <label className="block text-white/80 mb-3 font-medium">
                  Порог уверенности: {(confidenceThreshold * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-white"
                />
              </motion.div>
            )}

            {/* Индикатор загрузки */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6 text-center"
              >
                <Progress
                  isIndeterminate
                  aria-label="Обработка изображения"
                  className="max-w-md mx-auto"
                  color="primary"
                  size="lg"
                />
                <p className="text-white/70 mt-4">Обработка изображения...</p>
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-7xl p-8"
          >
            {/* Результаты */}
            <div className="space-y-8">
              {/* Заголовок результатов */}
              <div className="text-center mb-8">
                <h2 className="text-4xl font-bold mb-4 text-white">
                  ✅ Результаты детекции
                </h2>
                {results.has_defects && (
                  <div className="inline-block p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
                    <p className="text-yellow-300 font-semibold flex items-center gap-2">
                      <span className="text-2xl">⚠️</span>
                      <span>
                        Обнаружены дефекты! Найдено {results.defects_count}{" "}
                        {results.defects_count === 1 ? "дефектный объект" : "дефектных объекта"}.
                      </span>
                    </p>
                  </div>
                )}
              </div>

              {/* Изображение с детекциями */}
              <div className="mb-8">
                <div className="relative rounded-xl overflow-hidden border border-white/20 bg-black/50 p-4">
                  <div className="relative w-full flex justify-center items-center">
                    <img
                      ref={imageRef}
                      src={imagePreview || ""}
                      alt="Result"
                      className="max-w-full h-auto object-contain block rounded-lg"
                      onLoad={() => {
                        setTimeout(drawBoundingBoxes, 50);
                      }}
                    />
                    <canvas
                      ref={canvasRef}
                      className="absolute top-0 left-0 pointer-events-none"
                      style={{
                        imageRendering: "crisp-edges",
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Статистика */}
              <div className="mb-8">
                <h3 className="text-2xl font-bold mb-6 text-center text-white">
                  📊 Статистика объектов
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-6 rounded-xl bg-white/5 border border-white/10">
                    <div className="text-4xl mb-3">📦</div>
                    <h4 className="text-sm font-bold text-white/60 mb-3 uppercase">
                      Всего объектов
                    </h4>
                    <div className="text-4xl font-extrabold text-white">
                      {results.total_objects}
                    </div>
                  </div>
                  <div className={`text-center p-6 rounded-xl border ${
                    results.has_defects
                      ? "bg-red-500/10 border-red-500/30"
                      : "bg-green-500/10 border-green-500/30"
                  }`}>
                    <div className="text-4xl mb-3">
                      {results.has_defects ? "⚠️" : "✅"}
                    </div>
                    <h4 className="text-sm font-bold text-white/60 mb-3 uppercase">
                      Дефектов
                    </h4>
                    <div className={`text-4xl font-extrabold ${
                      results.has_defects ? "text-red-400" : "text-green-400"
                    }`}>
                      {results.defects_count}
                    </div>
                  </div>
                  <div className="text-center p-6 rounded-xl bg-white/5 border border-white/10">
                    <div className="text-4xl mb-3">🔧</div>
                    <h4 className="text-sm font-bold text-white/60 mb-3 uppercase">
                      Виброгасителей
                    </h4>
                    <div className="text-4xl font-extrabold text-white">
                      {results.statistics.vibration_damper || 0}
                    </div>
                  </div>
                  <div className="text-center p-6 rounded-xl bg-white/5 border border-white/10">
                    <div className="text-4xl mb-3">⚡</div>
                    <h4 className="text-sm font-bold text-white/60 mb-3 uppercase">
                      Изоляторов
                    </h4>
                    <div className="text-4xl font-extrabold text-white">
                      {(results.statistics.festoon_insulators || 0) +
                        (results.statistics.polymer_insulators || 0)}
                    </div>
                  </div>
                </div>
              </div>

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
              <div className="mt-8 text-center">
                <Button
                  variant="bordered"
                  className="border-white/30 text-white font-medium px-6 py-3 rounded-lg hover:bg-white/10"
                  onClick={clearFile}
                >
                  Загрузить новое изображение
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ошибка */}
      {error && (
        <div className="mt-6 p-6 bg-red-500/20 border border-red-500/50 rounded-xl">
          <p className="text-red-300 font-semibold flex items-center gap-2">
            <span className="text-2xl">❌</span>
            <span>Ошибка: {error}</span>
          </p>
        </div>
      )}
    </div>
  );
}

