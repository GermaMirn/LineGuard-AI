import { useCallback, useState, useRef, useEffect, useMemo, memo } from "react";
import { Button } from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
import { Virtuoso } from "react-virtuoso";

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

interface ImageSummary {
  detections?: Detection[];
  statistics?: Record<string, number>;
  total_objects?: number;
  defects_count?: number;
  has_defects?: boolean;
}

interface TaskImage {
  id: string;
  file_id: string;
  file_name: string;
  file_size: number;
  status: string;
  is_preview: boolean;
  summary?: ImageSummary | null;
  result_file_id?: string | null;
  error_message?: string | null;
  created_at: string;
  original_url: string;
  result_url?: string | null;
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
  images: TaskImage[];
  totalImages: number;
}

interface FileItemProps {
  image: TaskImage;
  previewUrl: string | null;
  hasDefects: boolean;
  formatFileSize: (bytes: number) => string;
  onOpenImage: (image: TaskImage, viewMode: 'original' | 'result') => void;
}

const FileItem = memo(({ image, previewUrl, hasDefects, formatFileSize, onOpenImage }: FileItemProps) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        menuRef.current &&
        !menuRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setIsMenuOpen(false);
      }
    };

    const updateMenuPosition = () => {
      if (buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        const menuWidth = 192; // w-48 = 192px
        let left = rect.right - menuWidth;

        // Проверяем, не выходит ли меню за правый край экрана
        if (left + menuWidth > window.innerWidth) {
          left = window.innerWidth - menuWidth - 8;
        }

        // Проверяем, не выходит ли меню за левый край экрана
        if (left < 8) {
          left = 8;
        }

        setMenuPosition({
          top: rect.bottom + 8,
          left: left,
        });
      }
    };

    const handleScroll = () => {
      setIsMenuOpen(false);
    };

    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      window.addEventListener("scroll", handleScroll, true);
      // Также слушаем скролл на контейнере со списком файлов
      const scrollContainer = document.querySelector('.overflow-y-auto');
      if (scrollContainer) {
        scrollContainer.addEventListener("scroll", handleScroll, true);
      }
      updateMenuPosition();
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", handleScroll, true);
      const scrollContainer = document.querySelector('.overflow-y-auto');
      if (scrollContainer) {
        scrollContainer.removeEventListener("scroll", handleScroll, true);
      }
    };
  }, [isMenuOpen]);

  const handleOpenOriginal = () => {
    onOpenImage(image, 'original');
    setIsMenuOpen(false);
  };

  const handleOpenResult = () => {
    onOpenImage(image, 'result');
    setIsMenuOpen(false);
  };

  const handleDownloadImages = useCallback(async () => {
    if (!image.file_id && !image.result_file_id) {
      return;
    }

    const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";

    const downloadFile = async (fileId: string, fileName: string) => {
      try {
        const response = await fetch(
          `${BFF_SERVICE_URL}/files/${fileId}/download`,
          { method: 'GET' }
        );

        if (!response.ok) {
          throw new Error(`Failed to download ${fileName}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error(`Error downloading ${fileName}:`, error);
        throw error;
      }
    };

    try {
      setIsDownloading(true);

      // Скачиваем оригинал
      if (image.file_id) {
        await downloadFile(image.file_id, `original_${image.file_name}`);
      }

      // Небольшая задержка между скачиваниями для стабильности
      await new Promise(resolve => setTimeout(resolve, 300));

      // Скачиваем результат, если он есть
      if (image.result_file_id) {
        await downloadFile(image.result_file_id, `result_${image.file_name}`);
      }
    } catch (error) {
      console.error("Error downloading images:", error);
      alert("Не удалось скачать файлы изображений");
    } finally {
      setIsDownloading(false);
      setIsMenuOpen(false);
    }
  }, [image]);

  const isDownloadAvailable = Boolean(image.file_id || image.result_file_id);

  return (
    <div className="grid grid-cols-[minmax(0,300px)_1fr_auto_auto] items-center gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl">
      {/* Иконка и название вместе */}
      <div className="flex items-center gap-4 min-w-0 max-w-[300px]">
        <div className="relative rounded-xl overflow-hidden bg-black/60 flex-shrink-0 w-14 h-14">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt={image.file_name}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <img
              src="/images/default-image.svg"
              alt="default-image"
              className="w-full h-full object-cover"
            />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-base font-semibold text-white truncate">
            {image.file_name}
          </h4>
        </div>
      </div>


      {/* Статус - по центру */}
      <div className="flex-shrink-0 justify-self-center">
        <span
          className={`px-3 py-1 text-xs font-semibold rounded-full ${
            hasDefects ? "bg-red-500/30 text-red-200" : "bg-emerald-500/30 text-emerald-100"
          }`}
        >
          {hasDefects ? "Поврежден" : "Без дефектов"}
        </span>
      </div>

      {/* Размер */}
      <div className="flex-shrink-0 text-sm text-white/80">
        {formatFileSize(image.file_size)}
      </div>

      {/* Меню (три точки) */}
      <div className="relative flex-shrink-0 ml-40">
        <button
          ref={buttonRef}
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          aria-label="Меню"
        >
          <svg
            className="w-5 h-5 text-white/80"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
            />
          </svg>
        </button>

        {/* Выпадающее меню */}
        {isMenuOpen && (
          <div
            ref={menuRef}
            className="fixed w-48 bg-white/10 backdrop-blur-md border border-white/20 rounded-lg shadow-lg z-[9999] overflow-hidden"
            style={{
              top: `${menuPosition.top}px`,
              left: `${menuPosition.left}px`,
            }}
          >
            <button
              onClick={handleOpenOriginal}
              className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors"
            >
              Вывести оригинал
            </button>
            <button
              onClick={handleOpenResult}
              disabled={!image.result_url}
              className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                image.result_url
                  ? "text-white hover:bg-white/10"
                  : "text-white/40 cursor-not-allowed"
              }`}
            >
              Вывести результат
            </button>
            <button
              onClick={handleDownloadImages}
              disabled={!isDownloadAvailable || isDownloading}
              className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                isDownloadAvailable && !isDownloading
                  ? "text-white hover:bg-white/10"
                  : "text-white/40 cursor-not-allowed"
              }`}
            >
              {isDownloading ? "Подготовка..." : "Скачать файлы"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
});

FileItem.displayName = 'FileItem';

// Мемоизированная карточка статистики
interface StatCardProps {
  imageSrc: string;
  imageAlt: string;
  value: number;
  label: string;
  shadowStyle?: React.CSSProperties;
}

const StatCard = memo(({ imageSrc, imageAlt, value, label, shadowStyle }: StatCardProps) => {
  return (
    <div
      className="relative text-center rounded-xl bg-white/5 overflow-hidden border border-white/20"
      style={shadowStyle}
    >
      <div className="relative z-10">
        <img
          src={imageSrc}
          alt={imageAlt}
          className="mx-auto drop-shadow-lg shadow-black/50 w-[100%] rounded-[10px]"
          loading="lazy"
          decoding="async"
          style={{
            contentVisibility: 'auto',
            willChange: 'transform',
          }}
        />
        <div className="flex flex-col items-start pl-4 pb-2" style={{marginTop: '-50px'}}>
          <div className="text-[56px] font-extrabold text-white">
            {value}
          </div>
          <h4 className="text-[16px] font-bold text-white/60 mb-3">
            {label}
          </h4>
        </div>
      </div>
    </div>
  );
});

StatCard.displayName = 'StatCard';

type SortType = "file_size" | "file_name" | "status" | null;
type SortDirection = "asc" | "desc";

export default function AnalysisHistoryContents({
  results,
  processedFilesCount,
  resultsArchiveFileId,
  images,
  totalImages,
}: AnalysisHistoryContentsProps) {
  const [sortType, setSortType] = useState<SortType>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [isFilterMenuOpen, setIsFilterMenuOpen] = useState(false);
  const filterMenuRef = useRef<HTMLDivElement>(null);
  const filterButtonRef = useRef<HTMLButtonElement>(null);
  const [filterMenuPosition, setFilterMenuPosition] = useState({ top: 0, left: 0 });

  // Состояния для просмотра изображений
  const [selectedImageForView, setSelectedImageForView] = useState<TaskImage | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'original' | 'result'>('original');

  const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL;

  // Предзагрузка изображений статистики при монтировании компонента
  useEffect(() => {
    const imagesToPreload = [
      '/images/folder.svg',
      '/images/objects.svg',
      '/images/danger.svg',
      '/images/smile-face.svg',
    ];

    imagesToPreload.forEach((src) => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = src;
      document.head.appendChild(link);
    });

    // Очистка при размонтировании не нужна, так как preload кешируется
  }, []);

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

  const formatFileSize = useCallback((bytes: number) => {
    if (!bytes && bytes !== 0) return "-";
    const units = ["Б", "КБ", "МБ", "ГБ"];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }

    return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
  }, []);

  const resolveImageUrl = useCallback((path?: string | null) => {
    if (!path) return null;
    if (/^https?:\/\//i.test(path)) {
      return path;
    }

    if (BFF_SERVICE_URL && BFF_SERVICE_URL !== "/api" && /^https?:\/\//i.test(BFF_SERVICE_URL)) {
      try {
        const base = new URL(BFF_SERVICE_URL);
        return `${base.origin}${path}`;
      } catch {
        return path;
      }
    }

    return path;
  }, [BFF_SERVICE_URL]);

  const getImageStatus = useCallback((image: TaskImage) => {
    if (typeof image.summary?.has_defects === "boolean") {
      return image.summary.has_defects;
    }

    if (typeof image.summary?.defects_count === "number") {
      return (image.summary.defects_count || 0) > 0;
    }

    return image.status?.toLowerCase() === "failed";
  }, []);

  // Обработка клика вне меню фильтрации
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        filterMenuRef.current &&
        !filterMenuRef.current.contains(target) &&
        filterButtonRef.current &&
        !filterButtonRef.current.contains(target)
      ) {
        setIsFilterMenuOpen(false);
      }
    };

    const updateFilterMenuPosition = () => {
      if (filterButtonRef.current) {
        const rect = filterButtonRef.current.getBoundingClientRect();
        const menuWidth = 200;
        let left = rect.left;

        if (left + menuWidth > window.innerWidth) {
          left = window.innerWidth - menuWidth - 8;
        }

        if (left < 8) {
          left = 8;
        }

        setFilterMenuPosition({
          top: rect.bottom + 8,
          left: left,
        });
      }
    };

    const handleScroll = () => {
      setIsFilterMenuOpen(false);
    };

    if (isFilterMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      window.addEventListener("scroll", handleScroll, true);
      // Также слушаем скролл на контейнере со списком файлов
      const scrollContainer = document.querySelector('.overflow-y-auto');
      if (scrollContainer) {
        scrollContainer.addEventListener("scroll", handleScroll, true);
      }
      updateFilterMenuPosition();
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", handleScroll, true);
      const scrollContainer = document.querySelector('.overflow-y-auto');
      if (scrollContainer) {
        scrollContainer.removeEventListener("scroll", handleScroll, true);
      }
    };
  }, [isFilterMenuOpen]);

  // Функция сортировки
  const sortedImages = useMemo(() => {
    if (!sortType) return images || [];

    const sorted = [...(images || [])].sort((a, b) => {
      let comparison = 0;

      switch (sortType) {
        case "file_size":
          comparison = a.file_size - b.file_size;
          break;
        case "file_name":
          comparison = a.file_name.localeCompare(b.file_name, "ru");
          break;
        case "status":
          const statusA = getImageStatus(a) ? 1 : 0;
          const statusB = getImageStatus(b) ? 1 : 0;
          comparison = statusA - statusB;
          break;
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });

    return sorted;
  }, [images, sortType, sortDirection, getImageStatus]);

  const handleSortChange = useCallback((type: SortType) => {
    if (sortType === type) {
      // Если выбран тот же тип, меняем направление
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Если новый тип, устанавливаем его и сбрасываем направление на asc
      setSortType(type);
      setSortDirection("asc");
    }
    setIsFilterMenuOpen(false);
  }, [sortType, sortDirection]);

  // Открытие изображения для просмотра
  const handleOpenImage = useCallback((image: TaskImage, mode: 'original' | 'result') => {
    const index = sortedImages.findIndex(img => img.id === image.id);
    setSelectedImageForView(image);
    setSelectedImageIndex(index);
    setViewMode(mode);
  }, [sortedImages]);

  // Закрытие просмотра
  const closeView = useCallback(() => {
    setSelectedImageForView(null);
    setSelectedImageIndex(null);
  }, []);

  // Переключение между изображениями
  const navigateImage = useCallback((direction: 'prev' | 'next') => {
    if (selectedImageIndex === null) return;

    let newIndex = selectedImageIndex;
    if (direction === 'prev' && selectedImageIndex > 0) {
      newIndex = selectedImageIndex - 1;
    } else if (direction === 'next' && selectedImageIndex < sortedImages.length - 1) {
      newIndex = selectedImageIndex + 1;
    }

    if (newIndex !== selectedImageIndex) {
      setSelectedImageIndex(newIndex);
      setSelectedImageForView(sortedImages[newIndex]);
    }
  }, [selectedImageIndex, sortedImages]);

  // Обработка клавиатуры для навигации в режиме просмотра
  useEffect(() => {
    if (!selectedImageForView) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeView();
      } else if (event.key === 'ArrowLeft') {
        navigateImage('prev');
      } else if (event.key === 'ArrowRight') {
        navigateImage('next');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedImageForView, closeView, navigateImage]);

  // Мемоизируем блок статистики для предотвращения лишних перерисовок
  const statsCards = useMemo(() => {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          imageSrc="/images/folder.svg"
          imageAlt="folder"
          value={processedFilesCount}
          label="Обработанных файлов"
        />
        <StatCard
          imageSrc="/images/objects.svg"
          imageAlt="objects"
          value={results.total_objects}
          label="Обнаруженных объектов"
        />
        <StatCard
          imageSrc="/images/danger.svg"
          imageAlt="danger"
          value={results.defects_count}
          label="Дефектов найдено"
          shadowStyle={{
            boxShadow: 'inset 0 0 20px rgba(255, 0, 0, 0.2), inset 0 0 15px rgba(255, 0, 0, 0.2), 0 0 10px rgba(255, 0, 0, 0.1)',
          }}
        />
        <StatCard
          imageSrc="/images/smile-face.svg"
          imageAlt="smile-face"
          value={results.total_objects - results.defects_count}
          label="Объектов без поломок"
          shadowStyle={{
            boxShadow: 'inset 0 0 20px rgba(0, 255, 8, 0.2), inset 0 0 15px rgba(0, 255, 8, 0.2), 0 0 10px rgba(255, 0, 0, 0.1)',
          }}
        />
      </div>
    );
  }, [processedFilesCount, results.total_objects, results.defects_count]);

  // Если открыт просмотр - показываем только просмотр
  if (selectedImageForView && selectedImageIndex !== null) {
    const currentImageUrl = viewMode === 'original'
      ? resolveImageUrl(selectedImageForView.original_url)
      : resolveImageUrl(selectedImageForView.result_url);

    return (
      <div
        className="h-full flex flex-col"
        style={{ padding: '34px 96px 64px' }}
      >
        {/* Список миниатюр для навигации */}
        {sortedImages.length > 0 && (() => {
          const itemWidth = 38;
          const itemGap = 16;
          const maxWidth = 528;
          const calculatedWidth = sortedImages.length * itemWidth + (sortedImages.length - 1) * itemGap;
          const containerWidth = Math.min(calculatedWidth, maxWidth);
          const containerHeight = 38;

          return (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative"
            >
              {/* Список миниатюр по центру */}
              <div className="flex justify-center">
                <div style={{ maxWidth: `${maxWidth}px`, width: `${containerWidth}px` }}>
                  <div className="pb-4">
                    <div
                      className="no-scroll flex gap-4"
                      style={{
                        height: `${containerHeight}px`,
                        width: `${containerWidth}px`,
                        overflowX: sortedImages.length > 10 ? 'auto' : 'hidden',
                        overflowY: 'hidden',
                        scrollbarWidth: 'none',
                        msOverflowStyle: 'none',
                      }}
                    >
                      {sortedImages.map((img, index) => {
                        const previewUrl = resolveImageUrl(img.result_url || img.original_url);
                        return (
                          <div
                            key={img.id}
                            className={`relative flex-shrink-0 overflow-hidden cursor-pointer hover:opacity-80 transition-all bg-white/10 flex items-center justify-center ${
                              selectedImageIndex === index ? 'ring-2 ring-white ring-offset-2 ring-offset-transparent' : ''
                            }`}
                            style={{
                              width: '38px',
                              height: '38px',
                              borderRadius: '8px',
                            }}
                            onClick={() => {
                              setSelectedImageIndex(index);
                              setSelectedImageForView(img);
                            }}
                          >
                            {previewUrl ? (
                              <img
                                src={previewUrl}
                                alt={img.file_name}
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                            ) : (
                              <div className="text-white/40 text-xs text-center px-1">
                                {index + 1}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
              {/* Кнопка закрытия в правом верхнем углу */}
              <button
                onClick={closeView}
                className="absolute top-1 right-0 z-10 h-[max-content] w-[max-content]"
                style={{ right: '-50px' }}
                aria-label="Закрыть"
              >
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </motion.div>
          );
        })()}

        {/* Просмотр изображения */}
        <div className="flex-1 relative flex items-center justify-center gap-6">
          {/* Изображение */}
          <div className="flex-1 flex items-center justify-center">
            {currentImageUrl ? (
              <img
                src={currentImageUrl}
                alt={selectedImageForView.file_name}
                className="max-w-full max-h-full object-contain rounded-lg mt-[-70px]"
              />
            ) : (
              <div className="flex items-center justify-center text-white/60">
                Изображение недоступно
              </div>
            )}
          </div>

          {/* Панель метрик (только для режима "Результат") */}
          <AnimatePresence>
            {viewMode === 'result' && selectedImageForView.summary?.detections && selectedImageForView.summary.detections.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
                className="w-80 h-full overflow-y-auto bg-black/60 backdrop-blur-sm rounded-lg p-4 space-y-4"
                style={{ maxHeight: 'calc(100vh - 200px)' }}
              >
              <div className="sticky top-0 bg-black/60 backdrop-blur-sm pb-2 border-b border-white/20">
                <h3 className="text-lg font-bold text-white">Метрики анализа</h3>
                <p className="text-sm text-white/60">
                  Обнаружено объектов: {selectedImageForView.summary.total_objects || selectedImageForView.summary.detections.length}
                </p>
              </div>

              <div className="space-y-3">
                {selectedImageForView.summary.detections.map((detection, index) => {
                  const isDefect = detection.defect_summary?.type && detection.defect_summary.type !== 'Норма';
                  const confidencePercent = (detection.confidence * 100).toFixed(1);

                  return (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${
                        isDefect
                          ? 'bg-red-500/10 border-red-500/30'
                          : 'bg-emerald-500/10 border-emerald-500/30'
                      }`}
                    >
                      {/* Класс объекта */}
                      <div className="flex items-center justify-between mb-2">
                        <span className={`text-sm font-semibold ${
                          isDefect ? 'text-red-300' : 'text-emerald-300'
                        }`}>
                          {detection.class_ru || detection.class}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          isDefect
                            ? 'bg-red-500/20 text-red-200'
                            : 'bg-emerald-500/20 text-emerald-200'
                        }`}>
                          {isDefect ? 'Дефект' : 'Норма'}
                        </span>
                      </div>

                      {/* Уверенность */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/60">Уверенность</span>
                          <span className="text-white font-semibold">{confidencePercent}%</span>
                        </div>
                        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              detection.confidence > 0.8
                                ? 'bg-green-500'
                                : detection.confidence > 0.6
                                ? 'bg-yellow-500'
                                : 'bg-orange-500'
                            }`}
                            style={{ width: `${confidencePercent}%` }}
                          />
                        </div>
                      </div>

                      {/* Информация о дефекте */}
                      {isDefect && detection.defect_summary && (
                        <div className="mt-2 pt-2 border-t border-white/10">
                          <p className="text-xs text-white/80 font-medium mb-1">
                            {detection.defect_summary.type}
                          </p>
                          {detection.defect_summary.description && (
                            <p className="text-xs text-white/60">
                              {detection.defect_summary.description}
                            </p>
                          )}
                          {detection.defect_summary.severity && (
                            <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${
                              detection.defect_summary.severity === 'high' || detection.defect_summary.severity === 'критическая'
                                ? 'bg-red-600/30 text-red-200'
                                : detection.defect_summary.severity === 'medium' || detection.defect_summary.severity === 'средняя'
                                ? 'bg-orange-600/30 text-orange-200'
                                : 'bg-yellow-600/30 text-yellow-200'
                            }`}>
                              Серьезность: {detection.defect_summary.severity}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Размер bbox */}
                      {detection.bbox_size && (
                        <div className="mt-2 text-xs text-white/50">
                          Размер: {Math.round(detection.bbox_size.width)}×{Math.round(detection.bbox_size.height)}px
                          {detection.bbox_size.is_small && ' (малый объект)'}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Кнопки переключения режима просмотра */}
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 flex gap-2 bg-black/60 backdrop-blur-sm rounded-lg p-2">
            <button
              onClick={() => setViewMode('original')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'original'
                  ? 'bg-white/20 text-white'
                  : 'text-white/60 hover:bg-white/10'
              }`}
            >
              Оригинал
            </button>
            <button
              onClick={() => setViewMode('result')}
              disabled={!selectedImageForView.result_url}
              className={`px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'result'
                  ? 'bg-white/20 text-white'
                  : selectedImageForView.result_url
                  ? 'text-white/60 hover:bg-white/10'
                  : 'text-white/30 cursor-not-allowed'
              }`}
            >
              Результат
            </button>
          </div>

          {/* Кнопки навигации */}
          {selectedImageIndex > 0 && (
            <button
              onClick={() => navigateImage('prev')}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 p-3 bg-black/60 backdrop-blur-sm rounded-full hover:bg-black/80 transition-colors"
              aria-label="Предыдущее изображение"
            >
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
          )}
          {selectedImageIndex < sortedImages.length - 1 && (
            <button
              onClick={() => navigateImage('next')}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 p-3 bg-black/60 backdrop-blur-sm rounded-full hover:bg-black/80 transition-colors"
              aria-label="Следующее изображение"
            >
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          )}

          {/* Информация о файле внизу */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-black/60 backdrop-blur-sm">
            <p className="text-white text-xl font-medium truncate text-center">
              {selectedImageForView.file_name}
            </p>
            <div className="flex items-center justify-center gap-4 mt-2">
              <p className="text-white/60 text-base">
                {formatFileSize(selectedImageForView.file_size)}
              </p>
              <p className="text-white/60 text-base">
                {selectedImageIndex + 1} / {sortedImages.length}
              </p>
              <p className={`text-base font-semibold ${
                getImageStatus(selectedImageForView) ? "text-red-300" : "text-emerald-300"
              }`}>
                {getImageStatus(selectedImageForView) ? "Поврежден" : "Без дефектов"}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
          {statsCards}

          {/* изображения по аналитике */}
          <div className="relative mb-6 h-[600px] border border-white/20 rounded-xl flex flex-col bg-white/5">
            <div className="p-4 flex flex-wrap gap-4 items-center justify-between">
              <div>
                <p className="font-bold text-lg">Загруженные файлы</p>
                <p className="text-white/60 text-sm">{totalImages} файлов в задаче</p>
              </div>

              <div className="flex gap-2 flex-wrap justify-end">
                <Button
                  size="lg"
                  className="text-white font-bold text-lg rounded-[10px] flex items-center justify-center h-[36px]"
                  radius="full"
                  style={{
                    padding: '9.5px 16px',
                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    fontWeight: 400
                  }}
                  onClick={downloadResultsArchive}
                  isDisabled={!resultsArchiveFileId}
                >
                  <img
                    src="/images/arhive.svg"
                    alt="archive"
                    className="mr-2"
                  />
                  Скачать архив
                </Button>

                <div className="relative">
                  <button
                    ref={filterButtonRef}
                    onClick={() => setIsFilterMenuOpen(!isFilterMenuOpen)}
                    className="text-white font-bold text-lg rounded-[10px] flex items-center justify-center h-[36px] border border-white/30 px-4"
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.15)',
                      fontWeight: 400
                    }}
                  >
                    <div className="flex flex-col mr-2">
                      <svg
                        className={`w-3 h-3 ${sortType && sortDirection === "asc" ? "opacity-100" : "opacity-50"}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 15l7-7 7 7"
                        />
                      </svg>
                      <svg
                        className={`w-3 h-3 ${sortType && sortDirection === "desc" ? "opacity-100" : "opacity-50"}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                    <span>Фильтрация</span>
                    <svg
                      className="w-4 h-4 ml-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>

                  {/* Выпадающее меню фильтрации */}
                  {isFilterMenuOpen && (
                    <div
                      ref={filterMenuRef}
                      className="fixed w-48 bg-white/10 backdrop-blur-md border border-white/20 rounded-lg shadow-lg z-[9999] overflow-hidden"
                      style={{
                        top: `${filterMenuPosition.top}px`,
                        left: `${filterMenuPosition.left}px`,
                      }}
                    >
                      <button
                        onClick={() => handleSortChange("file_size")}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                          sortType === "file_size"
                            ? "text-white bg-white/10"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        <span>Размер файла</span>
                        {sortType === "file_size" && (
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                      </button>
                      <button
                        onClick={() => handleSortChange("file_name")}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                          sortType === "file_name"
                            ? "text-white bg-white/10"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        <span>Имя файла</span>
                        {sortType === "file_name" && (
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                      </button>
                      <button
                        onClick={() => handleSortChange("status")}
                        className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                          sortType === "status"
                            ? "text-white bg-white/10"
                            : "text-white hover:bg-white/10"
                        }`}
                      >
                        <span>Статус</span>
                        {sortType === "status" && (
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <hr className="border-white/10" />
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Заголовки колонок */}
              {sortedImages.length > 0 && (
                <div className="px-4 pt-4 pb-2 grid grid-cols-[minmax(0,300px)_1fr_auto_auto] items-center gap-4">
                  <div className="flex items-center gap-4 min-w-0 max-w-[300px]">
                    <div className="w-14 flex-shrink-0"></div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white/80">Название файлов</p>
                    </div>
                  </div>
                  <div className="flex-shrink-0 justify-self-center">
                    <p className="text-sm font-semibold text-white/80">Статус</p>
                  </div>
                  <div className="flex-shrink-0" style={{ marginRight: '140px' }}>
                    <p className="text-sm font-semibold text-white/80">Размер</p>
                  </div>
                  <div className="w-10 flex-shrink-0 ml-8"></div>
                </div>
              )}
              <div className="h-full">
                {sortedImages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-white/60 text-center gap-2">
                    <p className="text-lg font-semibold">Файлов пока нет</p>
                    <p className="text-sm text-white/50 max-w-sm">
                      Как только обработка завершится, здесь появятся исходные и обработанные изображения с их статусом.
                    </p>
                  </div>
                ) : (
                  <Virtuoso
                    style={{ height: '100%', paddingTop: '16px', paddingBottom: '16px' }}
                    data={sortedImages}
                    overscan={200}
                    itemContent={(_index, image) => {
                      const previewUrl = resolveImageUrl(image.result_url || image.original_url);
                      const hasDefects = getImageStatus(image);

                      return (
                        <div style={{ marginBottom: '12px', paddingLeft: '16px', paddingRight: '16px' }}>
                          <FileItem
                            image={image}
                            previewUrl={previewUrl}
                            hasDefects={hasDefects}
                            formatFileSize={formatFileSize}
                            onOpenImage={handleOpenImage}
                          />
                        </div>
                      );
                    }}
                  />
                )}
              </div>
            </div>
          </div>
      </div>
    </motion.div>
  );
}

