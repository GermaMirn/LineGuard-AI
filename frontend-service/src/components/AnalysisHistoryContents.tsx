import { useCallback, useState, useRef, useEffect, useMemo } from "react";
import { Button } from "@heroui/react";
import { motion } from "framer-motion";

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
  resolveImageUrl: (path?: string | null) => string | null;
}

function FileItem({ image, previewUrl, hasDefects, formatFileSize, resolveImageUrl }: FileItemProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

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
    if (image.original_url) {
      window.open(resolveImageUrl(image.original_url) || "", "_blank");
    }
    setIsMenuOpen(false);
  };

  const handleOpenResult = () => {
    if (image.result_url) {
      window.open(resolveImageUrl(image.result_url) || "", "_blank");
    }
    setIsMenuOpen(false);
  };

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
          </div>
        )}
      </div>
    </div>
  );
}

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

  const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL;

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
            <div className="relative text-center rounded-xl bg-white/5 overflow-hidden border border-white/20">
              <div className="relative z-10">
                <img
                  src="/images/folder.svg"
                  alt="folder"
                  className="mx-auto drop-shadow-lg shadow-black/50 w-[100%] rounded-[10px]"
                />
                 <div className="flex flex-col items-start pl-4 pb-2" style={{marginTop: '-50px'}}>
                   <div className="text-[56px] font-extrabold text-white">
                     {processedFilesCount}
                   </div>
                   <h4 className="text-[16px] font-bold text-white/60 mb-3">
                     Обработанных файлов
                   </h4>
                 </div>
              </div>
            </div>
            <div className="relative text-center rounded-xl bg-white/5 overflow-hidden border border-white/20">
              <div className="relative z-10">
                <img
                  src="/images/objects.svg"
                  alt="objects"
                  className="mx-auto drop-shadow-lg shadow-black/50 w-[100%] rounded-[10px]"
                />

                <div className="flex flex-col items-start pl-4 pb-2" style={{marginTop: '-50px'}}>
                  <div className="text-[56px] font-extrabold text-white">
                  {results.total_objects}
                  </div>
                  <h4 className="text-[16px] font-bold text-white/60 mb-3">
                    Обнаруженных объектов
                  </h4>
                </div>
              </div>
            </div>
            <div
              className="relative text-center rounded-xl bg-white/5 overflow-hidden border border-white/20"
              style={{boxShadow: 'inset 0 0 20px rgba(255, 0, 0, 0.2), inset 0 0 15px rgba(255, 0, 0, 0.2), 0 0 10px rgba(255, 0, 0, 0.1)',}}
            >

              <div className="relative z-10">
                <img
                  src="/images/danger.svg"
                  alt="danger"
                  className="mx-auto drop-shadow-lg shadow-black/50 w-[100%] rounded-[10px]"
                />
                <div className="flex flex-col items-start pl-4 pb-2" style={{marginTop: '-50px'}}>
                  <div className="text-[56px] font-extrabold text-white">
                  {results.defects_count}
                  </div>
                  <h4 className="text-[16px] font-bold text-white/60 mb-3">
                    Дефектов найдено
                  </h4>
                </div>
              </div>
            </div>
            <div
              className="text-center rounded-xl bg-white/5 border border-white/20"
              style={{boxShadow: 'inset 0 0 20px rgba(0, 255, 8, 0.2), inset 0 0 15px rgba(0, 255, 8, 0.2), 0 0 10px rgba(255, 0, 0, 0.1)',}}
            >
              <img
                src="/images/smile-face.svg"
                alt="smile-face"
                className="mx-auto drop-shadow-lg shadow-black/50 w-[100%] rounded-[10px]"
              />

              <div className="flex flex-col items-start pl-4 pb-2" style={{marginTop: '-50px'}}>
                <div className="text-[56px] font-extrabold text-white">
                {results.total_objects - results.defects_count}
                </div>
                <h4 className="text-[16px] font-bold text-white/60 mb-3">
                  Объектов без поломок
                </h4>
              </div>
            </div>
          </div>

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
              <div className="h-full overflow-y-auto p-4 space-y-3">
                {sortedImages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-white/60 text-center gap-2">
                    <p className="text-lg font-semibold">Файлов пока нет</p>
                    <p className="text-sm text-white/50 max-w-sm">
                      Как только обработка завершится, здесь появятся исходные и обработанные изображения с их статусом.
                    </p>
                  </div>
                ) : (
                  sortedImages.map((image: TaskImage) => {
                    const previewUrl = resolveImageUrl(image.result_url || image.original_url);
                    const hasDefects = getImageStatus(image);

                    return (
                      <FileItem
                        key={image.id}
                        image={image}
                        previewUrl={previewUrl}
                        hasDefects={hasDefects}
                        formatFileSize={formatFileSize}
                        resolveImageUrl={resolveImageUrl}
                      />
                    );
                  })
                )}
              </div>
            </div>
          </div>

        {/* Детекции */}
        {/* {results.detections && results.detections.length > 0 && (
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
        )} */}

        {/* Кнопка возврата */}
        {/* {onBack && (
          <div className="mt-8 text-center">
            <Button
              variant="bordered"
              className="border-white/30 text-white font-medium px-6 py-3 rounded-lg hover:bg-white/10"
              onClick={onBack}
            >
              Загрузить новые изображения
            </Button>
          </div>
        )} */}
      </div>
    </motion.div>
  );
}

