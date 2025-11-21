import { motion } from "framer-motion";
import { useState } from "react";
import { ScrollShadow } from "@heroui/react";

interface FileWithPreview {
  file: File;
  preview: string | null;
  id: string;
}

interface PhotoThumbnailsProps {
  files: FileWithPreview[];
  selectedIndex: number | null;
  onSelectImage: (file: FileWithPreview, index: number) => void;
  onRemoveImage: (id: string) => void;
  onLoadPreview: (file: FileWithPreview) => void;
  disableModal?: boolean; // Отключить переход в модалку при клике
  onSelect?: (index: number) => void; // Только выбор без перехода
  fastDelete?: boolean; // Быстрое удаление при наведении
  disableDelete?: boolean; // Отключить удаление (например, во время анализа)
}

export default function PhotoThumbnails({
  files,
  selectedIndex,
  onSelectImage,
  onRemoveImage,
  onLoadPreview,
  disableModal = false,
  onSelect,
  fastDelete = false,
  disableDelete = false,
}: PhotoThumbnailsProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Функция для форматирования имени файла: максимум 7 символов + "..." + расширение
  const formatFileName = (fileName: string): string => {
    const lastDotIndex = fileName.lastIndexOf('.');
    if (lastDotIndex === -1) {
      // Нет расширения
      return fileName.length > 7 ? `${fileName.substring(0, 7)}...` : fileName;
    }

    const nameWithoutExt = fileName.substring(0, lastDotIndex);
    const extension = fileName.substring(lastDotIndex);

    if (nameWithoutExt.length <= 7) {
      return fileName;
    }

    return `${nameWithoutExt.substring(0, 7)}...${extension}`;
  };

  if (files.length === 0) return null;

  // Динамически рассчитываем ширину контейнера на основе количества фотографий
  const photosCount = Math.min(files.length, 10); // Максимум 10 фотографий видимых
  const photoSize = 48; // Максимальный размер фотографии (с учётом увеличения)
  const gap = 16; // Расстояние между фотографиями
  const horizontalPadding = fastDelete ? 16 : 16; // Padding слева и справа
  const verticalPadding = fastDelete ? 12 : 16; // Padding сверху и снизу

  // Если файлов больше 10, используем maxWidth, иначе рассчитываем точную ширину
  const useFixedWidth = files.length <= 10;
  const calculatedWidth = (horizontalPadding * 2) + (photosCount * photoSize) + ((photosCount - 1) * gap);

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto relative"
      style={{
        width: useFixedWidth ? `${calculatedWidth}px` : undefined,
        maxWidth: useFixedWidth ? undefined : '656px',
        padding: `${verticalPadding}px ${horizontalPadding}px`,
        overflow: 'visible',
      }}
    >
      {/* Фон с border-radius - псевдоэлемент через inline style не работает, используем абсолютный div */}
      <div
        className="absolute inset-0 border-2 border-white/20 rounded-2xl bg-black/60 pointer-events-none"
        style={{ zIndex: 0 }}
      />

      {/* Контент поверх фона */}
      <div className="relative" style={{ zIndex: 1, overflow: 'visible' }}>
      {/* Список миниатюр */}
      <ScrollShadow
        orientation="horizontal"
        hideScrollBar
        className="flex gap-4 hide-scrollbar"
        style={{
          overflowY: 'visible',
          overflowX: 'auto',
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
          position: 'relative',
        }}
      >
        {files.map((fileWithPreview, index) => {
          const isSelected = selectedIndex === index;
          const isHovered = hoveredIndex === index;
          const shouldEnlarge = fastDelete ? (isHovered || isSelected) : isSelected;

          // Загружаем превью для видимых элементов
          if (!fileWithPreview.preview) {
            setTimeout(() => onLoadPreview(fileWithPreview), 0);
          }

          return (
            <div
              key={fileWithPreview.id}
              className="flex-shrink-0 flex flex-col items-center"
              style={{
                width: '48px',
                position: 'relative',
                overflow: 'visible',
              }}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <div className="relative" style={{ width: '48px', height: '48px', overflow: 'visible', position: 'relative' }}>
                <div
                  className="absolute cursor-pointer transition-all"
                  style={{
                    width: shouldEnlarge ? '48px' : '38px',
                    height: shouldEnlarge ? '48px' : '38px',
                    top: shouldEnlarge ? '0' : '5px',
                    left: shouldEnlarge ? '0' : '5px',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    zIndex: shouldEnlarge ? 10 : 1,
                  }}
                  onClick={() => {
                    if (disableModal && onSelect) {
                      onSelect(index);
                    } else if (!disableModal) {
                      onSelectImage(fileWithPreview, index);
                    }
                  }}
                >
                  {/* Изображение */}
                  {fileWithPreview.preview ? (
                    <img
                      src={fileWithPreview.preview}
                      alt={fileWithPreview.file.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full bg-white/10 flex items-center justify-center">
                      <div className="text-white/40 text-sm">
                        {index + 1}
                      </div>
                    </div>
                  )}
                </div>

                {/* Кнопка удаления - показывается при наведении (fastDelete) или выделении, поверх всего */}
                {(fastDelete ? isHovered : isSelected) && !disableDelete && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!disableDelete) {
                        onRemoveImage(fileWithPreview.id);
                      }
                    }}
                    className="absolute w-5 h-5 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-600 transition-colors shadow-lg"
                    style={{
                      top: shouldEnlarge ? '-4px' : '2px',
                      right: shouldEnlarge ? '-4px' : '2px',
                      zIndex: 10000,
                      position: 'absolute',
                    }}
                    aria-label="Удалить"
                    disabled={disableDelete}
                  >
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>

              {/* Название файла под каждым изображением - место зарезервировано, показывается при наведении или выборе */}
              <div className="mt-1 text-center truncate w-full" style={{ maxWidth: '48px', minHeight: '16px' }}>
                {(isHovered || isSelected) && (
                  <p className="text-white text-xs font-medium">
                    {formatFileName(fileWithPreview.file.name)}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </ScrollShadow>
      {/* Закрываем div контента */}
      </div>
    </motion.div>
  );
}

