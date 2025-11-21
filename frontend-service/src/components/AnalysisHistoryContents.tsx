import { useCallback, useState, useRef, useEffect, useMemo, memo } from "react";
import { Card, CardBody, ScrollShadow } from "@heroui/react";
import { motion } from "framer-motion";
import { Virtuoso } from "react-virtuoso";
import Breadcrumbs from "./Breadcrumbs";
import PhotoThumbnails from "./PhotoThumbnails";
import ImageAnnotationTool from "./ImageAnnotationTool";
import { getDefectType, getDefectMetadata, getDefectTypeName } from "@/types/metrics";

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
  thumbnail?: string | null;  // base64 thumbnail для оптимизации
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
  routeName?: string | null;
  taskId?: string | null;
  onImageDeleted?: (imageId: string) => void;
  onViewModeChange?: (isViewing: boolean) => void;
}

interface FileItemProps {
  image: TaskImage;
  previewUrl: string | null;
  hasDefects: boolean;
  formatFileSize: (bytes: number) => string;
  onOpenImage: (image: TaskImage, viewMode: 'original' | 'result') => void;
  onDeleteImage: (imageId: string) => void;
}

// Мемоизированный компонент изображения
interface ImageViewerProps {
  imageUrl: string | null;
  imageName: string;
  imageVersion: number;
  imageId: string;
  viewMode: 'original' | 'result';
}

const ImageViewer = memo(({ imageUrl, imageName, imageVersion, imageId, viewMode }: ImageViewerProps) => {
  return (
    <div className="relative inline-block max-w-full max-h-full">
      <img
        key={`${imageId}-${viewMode}-${imageVersion}`}
        src={imageUrl || undefined}
        alt={imageName}
        className="object-contain"
        style={{ maxWidth: '100%', maxHeight: '100%', width: 'auto', height: 'auto' }}
        onLoad={() => {
          // Изображение загрузилось успешно
          console.log('Image loaded:', imageUrl);
        }}
      />
    </div>
  );
});

ImageViewer.displayName = 'ImageViewer';

const FileItem = memo(({ image, previewUrl, hasDefects, formatFileSize, onOpenImage, onDeleteImage }: FileItemProps) => {
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

  const handleDeleteImage = useCallback(() => {
    onDeleteImage(image.id);
    setIsMenuOpen(false);
  }, [image, onDeleteImage]);

  const isDownloadAvailable = Boolean(image.file_id || image.result_file_id);

  return (
    <div
      className="grid grid-cols-[minmax(0,300px)_1fr_auto_auto] items-center gap-4 p-2 bg-white/5 border border-white/10 rounded-2xl cursor-pointer hover:bg-white/10 transition-colors"
      onClick={() => onOpenImage(image, 'result')}
    >
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
          onClick={(e) => {
            e.stopPropagation();
            setIsMenuOpen(!isMenuOpen);
          }}
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
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleOpenResult();
              }}
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
              onClick={(e) => {
                e.stopPropagation();
                handleDownloadImages();
              }}
              disabled={!isDownloadAvailable || isDownloading}
              className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                isDownloadAvailable && !isDownloading
                  ? "text-white hover:bg-white/10"
                  : "text-white/40 cursor-not-allowed"
              }`}
            >
              {isDownloading ? "Подготовка..." : "Скачать файлы"}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteImage();
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            >
              Удалить фотографию
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
  routeName,
  taskId,
  onImageDeleted,
  onViewModeChange,
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
  const [, setShowMetricsPanel] = useState<boolean>(false);
  const [isAnnotationMode, setIsAnnotationMode] = useState<boolean>(false);
  const [imageVersion, setImageVersion] = useState<number>(0); // Версия изображения для принудительной перезагрузки

  const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL;

  // Уведомляем родительский компонент об изменении режима просмотра
  useEffect(() => {
    if (onViewModeChange) {
      onViewModeChange(selectedImageForView !== null);
    }
  }, [selectedImageForView, onViewModeChange]);

  // Функция закрытия просмотра
  const closeView = useCallback(() => {
    setSelectedImageForView(null);
    setSelectedImageIndex(null);
    setShowMetricsPanel(false);
  }, []);

  // Сохраняем функцию закрытия для использования извне
  useEffect(() => {
    (window as any).__closeHistoryImageView = closeView;
    return () => {
      delete (window as any).__closeHistoryImageView;
    };
  }, [closeView]);

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
    // Меню не закрывается после выбора
  }, [sortType, sortDirection]);

  // Открытие изображения для просмотра
  const handleOpenImage = useCallback((image: TaskImage, mode: 'original' | 'result') => {
    const index = sortedImages.findIndex(img => img.id === image.id);
    setSelectedImageForView(image);
    setSelectedImageIndex(index);
    setViewMode(mode);
    // Сбрасываем версию изображения при смене изображения
    setImageVersion(0);
    // Автоматически открываем панель метрик для режима результата
    setShowMetricsPanel(mode === 'result');
  }, [sortedImages]);

  // Удаление изображения
  const handleDeleteImage = useCallback(async (imageId: string) => {
    if (!taskId) {
      alert("Не удалось определить задачу");
      return;
    }

    try {
      const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
      const response = await fetch(
        `${BFF_SERVICE_URL}/analysis/tasks/${taskId}/images/${imageId}`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete image');
      }

      // Если изображение было удалено успешно, вызываем callback с imageId
      if (onImageDeleted) {
        onImageDeleted(imageId);
      }
    } catch (error) {
      console.error("Error deleting image:", error);
      alert("Не удалось удалить фотографию");
    }
  }, [taskId, onImageDeleted]);

  // Удаление изображения из режима просмотра
  const handleRemoveImageFromView = useCallback(async (fileId: string) => {
    if (!taskId || selectedImageIndex === null) {
      return;
    }

    try {
      // Находим индекс удаляемого изображения
      const imageToDeleteIndex = sortedImages.findIndex(img => img.id === fileId);
      if (imageToDeleteIndex === -1) {
        return;
      }

      // Удаляем через API
      const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
      const response = await fetch(
        `${BFF_SERVICE_URL}/analysis/tasks/${taskId}/images/${fileId}`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete image');
      }

      // Вызываем callback родительского компонента
      if (onImageDeleted) {
        onImageDeleted(fileId);
      }

      // Определяем, какое изображение показать после удаления
      const remainingImages = sortedImages.filter(img => img.id !== fileId);

      if (remainingImages.length === 0) {
        // Если это было последнее изображение - закрываем просмотр
        closeView();
      } else {
        // Если удалили текущее изображение, переключаемся на следующее или предыдущее
        if (imageToDeleteIndex === selectedImageIndex) {
          // Выбираем следующее изображение, или если удалили последнее - предыдущее
          const newIndex = imageToDeleteIndex < remainingImages.length
            ? imageToDeleteIndex
            : remainingImages.length - 1;

      setSelectedImageIndex(newIndex);
          setSelectedImageForView(remainingImages[newIndex]);
        } else if (imageToDeleteIndex < selectedImageIndex) {
          // Если удалили изображение до текущего, сдвигаем индекс
          setSelectedImageIndex(selectedImageIndex - 1);
        }
      }
    } catch (error) {
      console.error("Error deleting image:", error);
      alert("Не удалось удалить фотографию");
    }
  }, [taskId, sortedImages, selectedImageIndex, onImageDeleted, closeView]);

  // Обработка клавиатуры для закрытия просмотра
  useEffect(() => {
    if (!selectedImageForView) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeView();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedImageForView, closeView]);

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
    // Добавляем версию к URL для принудительной перезагрузки изображения
    const baseImageUrl = viewMode === 'original'
      ? resolveImageUrl(selectedImageForView.original_url)
      : resolveImageUrl(selectedImageForView.result_url);

    // Добавляем параметр версии для обхода кеша браузера
    const currentImageUrl = baseImageUrl
      ? `${baseImageUrl}${baseImageUrl.includes('?') ? '&' : '?'}v=${imageVersion}`
      : null;

    // Преобразуем изображения в формат для PhotoThumbnails
    const filesForThumbnails = sortedImages.map((img) => ({
      file: new File([], img.file_name),
      preview: img.thumbnail || resolveImageUrl(img.result_url || img.original_url),
      id: img.id,
    }));

    // URL для аннотации (используем базовый URL без версии, так как это будет актуальное изображение)
    const baseAnnotationImageUrl = viewMode === 'original'
      ? resolveImageUrl(selectedImageForView.original_url)
      : resolveImageUrl(selectedImageForView.result_url);

    const annotationImageUrl = baseAnnotationImageUrl
      ? `${baseAnnotationImageUrl}${baseAnnotationImageUrl.includes('?') ? '&' : '?'}v=${imageVersion}`
      : null;

    return (
      <>
      <div
        className="h-full flex flex-col"
        style={{ padding: '48px 96px' }}
      >
        {/* Просмотр изображения и метрики */}
        <div className="flex-1 flex flex-col gap-4 overflow-hidden">
          {/* Контейнер изображения */}
          <div className="flex-1 flex items-center justify-center overflow-hidden relative">
            {currentImageUrl ? (
              <div className="relative inline-block max-w-full max-h-full">
                <ImageViewer
                  imageUrl={currentImageUrl}
                  imageName={selectedImageForView.file_name}
                  imageVersion={imageVersion}
                  imageId={selectedImageForView.id}
                  viewMode={viewMode}
                />

                {/* PhotoThumbnails компонент - по центру сверху на фотографии */}
                <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
                  className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10"
                >
                  <PhotoThumbnails
                    files={filesForThumbnails}
                    selectedIndex={selectedImageIndex}
                    onSelectImage={(_file, index) => {
                      setSelectedImageIndex(index);
                      setSelectedImageForView(sortedImages[index]);
                      setImageVersion(0); // Сбрасываем версию при смене изображения
                    }}
                    onRemoveImage={handleRemoveImageFromView}
                    onLoadPreview={() => {}} // Превью уже загружены
                    disableModal={true}
                    onSelect={(index) => {
                      setSelectedImageIndex(index);
                      setSelectedImageForView(sortedImages[index]);
                      setImageVersion(0); // Сбрасываем версию при смене изображения
                    }}
                  />
                </motion.div>

                {/* Кнопки переключения режима просмотра - по центру внизу на фотографии */}
                <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2 bg-black/60 backdrop-blur-sm rounded-lg p-1 z-10">
                  <button
                            onClick={() => {
                      setViewMode('original');
                      setShowMetricsPanel(false);
                      setImageVersion(0); // Сбрасываем версию при смене режима
                    }}
                    className={`px-3 py-1.5 rounded-md transition-colors text-sm ${
                      viewMode === 'original'
                        ? 'bg-white/20 text-white'
                        : 'text-white/60 hover:bg-white/10'
                    }`}
                  >
                    Оригинал
                  </button>
              <button
                    onClick={() => {
                      setViewMode('result');
                      setShowMetricsPanel(true);
                      setImageVersion(0); // Сбрасываем версию при смене режима
                    }}
                    disabled={!selectedImageForView.result_url}
                    className={`px-3 py-1.5 rounded-md transition-colors text-sm ${
                      viewMode === 'result'
                        ? 'bg-white/20 text-white'
                        : selectedImageForView.result_url
                        ? 'text-white/60 hover:bg-white/10'
                        : 'text-white/30 cursor-not-allowed'
                    }`}
                  >
                    Результат
                  </button>
                  <button
                    onClick={() => setIsAnnotationMode(true)}
                    disabled={!selectedImageForView.result_url}
                    className={`px-3 py-1.5 rounded-md transition-colors text-sm flex items-center gap-1.5 ${
                      selectedImageForView.result_url
                        ? 'text-white/60 hover:bg-white/10'
                        : 'text-white/30 cursor-not-allowed'
                    }`}
                    title="Инструмент для выделения областей"
              >
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
                        d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                  />
                </svg>
                    Выделить
              </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center text-white/60">
                Изображение недоступно
              </div>
            )}
          </div>

          {/* Карточки метрик под изображением - скроллируемые */}
          <div style={{ minHeight: '180px', display: 'flex', alignItems: 'flex-end', width: '100%' }}>
            {viewMode === 'result' && selectedImageForView.summary?.detections && selectedImageForView.summary.detections.length > 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ duration: 0.3 }}
                className="w-full"
              >
                <ScrollShadow
                  orientation="horizontal"
                  hideScrollBar
                  className="flex gap-4 hide-scrollbar border border-solid border-white/20 rounded-[14px] p-[8px]"
                  style={{
                    scrollbarWidth: 'none',
                    msOverflowStyle: 'none',
                  }}
              >
                {selectedImageForView.summary.detections
                  .slice()
                  .sort((a, b) => {
                    // Сортировка: сначала дефекты, потом обычные объекты
                    const isDefectA = a.defect_summary?.type &&
                                     a.defect_summary.type !== 'Норма' &&
                                     a.defect_summary.severity !== 'none' &&
                                     a.defect_summary.severity !== null;
                    const isDefectB = b.defect_summary?.type &&
                                     b.defect_summary.type !== 'Норма' &&
                                     b.defect_summary.severity !== 'none' &&
                                     b.defect_summary.severity !== null;

                    if (isDefectA && !isDefectB) return -1;
                    if (!isDefectA && isDefectB) return 1;

                    // Внутри дефектов: критические первые, потом предупреждения
                    if (isDefectA && isDefectB) {
                      const severityA = a.defect_summary?.severity;
                      const severityB = b.defect_summary?.severity;
                      const isCriticalA = severityA === 'high' || severityA === 'критическая';
                      const isCriticalB = severityB === 'high' || severityB === 'критическая';

                      if (isCriticalA && !isCriticalB) return -1;
                      if (!isCriticalA && isCriticalB) return 1;
                    }

                    return 0;
                  })
                  .map((detection, index) => {
                  // Определяем тип и severity дефекта
                  const isDefect = detection.defect_summary?.type &&
                                   detection.defect_summary.type !== 'Норма' &&
                                   detection.defect_summary.severity !== 'none' &&
                                   detection.defect_summary.severity !== null;

                  const severity = detection.defect_summary?.severity;

                  // Используем новую систему метрик
                  const metadata = getDefectMetadata(severity, Boolean(isDefect));
                  const defectType = getDefectType(
                    detection.class_ru || detection.class,
                    detection.defect_summary?.type
                  );
                  const defectTypeName = getDefectTypeName(defectType);

                  const confidencePercent = (detection.confidence * 100).toFixed(0);

                  return (
                    <Card
                      key={index}
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
                        <h4 className="text-base font-semibold text-white flex-1 min-w-0 truncate">
                          {detection.class_ru || detection.class}
                          </h4>
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
                              backgroundColor: '#10B981' // Зеленый цвет как на скриншоте
                            }}
                          />
                        </div>
                      </div>

                      {/* Тип повреждения */}
                      {isDefect && detection.defect_summary && defectTypeName && (
                        <div>
                          <p className="text-sm text-white/90">
                            Тип повреждения: <span className="font-semibold">
                              {defectTypeName}
                            </span>
                          </p>
                        </div>
                      )}
                      </CardBody>
                    </Card>
                  );
                })}
              </ScrollShadow>
              </motion.div>
            ) : (
              <div></div>
            )}
          </div>
        </div>
          </div>

        {/* Компонент аннотации - рендерится поверх всего */}
        {isAnnotationMode && taskId && annotationImageUrl && (
          <ImageAnnotationTool
            imageUrl={annotationImageUrl}
            imageId={selectedImageForView.id}
            taskId={taskId}
            fileId={viewMode === 'result' && selectedImageForView.result_file_id
              ? selectedImageForView.result_file_id
              : selectedImageForView.file_id}
            projectId={taskId} // Используем taskId как project_id
            onClose={() => setIsAnnotationMode(false)}
            onImageUpdated={() => {
              // Увеличиваем версию изображения для принудительной перезагрузки
              // Это заставит браузер загрузить новое изображение с аннотациями
              setImageVersion(prev => prev + 1);

              // Небольшая задержка перед закрытием модалки, чтобы изображение успело обновиться
              // Версия увеличится, annotationImageUrl пересчитается, и модалка получит новый imageUrl
              setTimeout(() => {
                // Модалка закроется автоматически после сохранения
              }, 300);
            }}
          />
        )}
      </>
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
      style={{ padding: '42px 96px 48px' }}
    >
      {/* Хлебные крошки */}
      <div className="mb-2">
        <Breadcrumbs
          items={[
            { label: "Главная", path: "/" },
            { label: "История", path: "/history" },
            { label: routeName || "Результаты анализа" }
          ]}
        />
      </div>

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
                    <span>Фильтрация</span>
                    <svg
                      className={`w-4 h-4 ml-2 transition-transform ${isFilterMenuOpen ? 'rotate-180' : ''}`}
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
                              d={sortDirection === "asc" ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}
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
                              d={sortDirection === "asc" ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}
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
                              d={sortDirection === "asc" ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}
                            />
                          </svg>
                        )}
                      </button>
                    </div>
                  )}
                </div>

                <button
                  className="text-white font-bold text-lg rounded-[10px] flex items-center justify-center h-[36px] border border-white/30 px-4"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    fontWeight: 400
                  }}
                  onClick={downloadResultsArchive}
                  disabled={!resultsArchiveFileId}
                >
                  <img
                    src="/images/arhive.svg"
                    alt="archive"
                    className="mr-2"
                  />
                  <span>Скачать архив</span>
                </button>
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
                      // Используем thumbnail если есть, иначе fallback на URL
                      const previewUrl = image.thumbnail || resolveImageUrl(image.result_url || image.original_url);
                      const hasDefects = getImageStatus(image);

                      return (
                        <div style={{ marginBottom: '12px', paddingLeft: '16px', paddingRight: '16px' }}>
                          <FileItem
                            image={image}
                            previewUrl={previewUrl}
                            hasDefects={hasDefects}
                            formatFileSize={formatFileSize}
                            onOpenImage={handleOpenImage}
                            onDeleteImage={handleDeleteImage}
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

