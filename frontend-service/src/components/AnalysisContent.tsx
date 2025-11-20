import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Progress } from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
import { Virtuoso } from "react-virtuoso";
import apiClient from "@/shared/api/axios";
import AnalysisLoader from "./AnalysisLoader";


const MAX_SIZE_BYTES = 10 * 1024 * 1024 * 1024; // 10 GB
const SUPPORTED_IMAGE_TYPES = [
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/tiff",
  "image/tif",
  "image/bmp",
  "image/dng",
  "image/raw",
  "image/nef",
  "image/cr2",
  "image/arw",
];

interface FileWithPreview {
  file: File;
  preview: string | null;
  id: string;
}

interface AnalysisProgress {
  task_id: string;
  status: string;
  processed_files: number;
  total_files: number;
  failed_files: number;
  defects_found: number;
  message?: string;
}

interface AnalysisContentProps {
  onViewModeChange?: (isViewing: boolean) => void;
}

export default function AnalysisContent({ onViewModeChange }: AnalysisContentProps = {}) {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confidenceThreshold] = useState(0.5);
  const [routeName, setRouteName] = useState<string>("");
  const [selectedImageForView, setSelectedImageForView] = useState<FileWithPreview | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Уведомляем родительский компонент об изменении режима просмотра
  useEffect(() => {
    if (onViewModeChange) {
      onViewModeChange(selectedImageForView !== null);
    }
  }, [selectedImageForView, onViewModeChange]);

  // Сохраняем функцию закрытия для использования извне
  const closeView = useCallback(() => {
    setSelectedImageForView(null);
    setSelectedImageIndex(null);
  }, []);

  useEffect(() => {
    // Сохраняем функцию закрытия в window для доступа из AnalysisPage
    (window as any).__closeImageView = closeView;
    return () => {
      delete (window as any).__closeImageView;
    };
  }, [closeView]);

  // WebSocket подключение для получения статуса анализа
  useEffect(() => {
    if (!currentTaskId) return;

    const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${BFF_SERVICE_URL}/ws/tasks/${currentTaskId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected to:', wsUrl);
    };

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data) as AnalysisProgress;
        console.log('WebSocket message received:', data);
        setAnalysisProgress(data);

        // Если анализ завершен или провалился, перенаправляем на страницу результатов
        // Статус приходит в нижнем регистре: 'completed', 'failed', 'processing'
        const statusUpper = data.status?.toUpperCase();
        if (statusUpper === 'COMPLETED' || statusUpper === 'FAILED') {
          setLoading(false);

          // Перенаправляем на страницу результатов с task_id
          const taskIdToLoad = data.task_id || currentTaskId;
          if (statusUpper === 'COMPLETED' && taskIdToLoad) {
            // Перенаправляем на страницу с результатами
            navigate(`/panel?model=analysis&task_id=${taskIdToLoad}`);
          } else if (statusUpper === 'FAILED') {
            setError('Анализ завершился с ошибкой');
          }

          ws.close();
          wsRef.current = null;
          setCurrentTaskId(null);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      console.error('WebSocket URL was:', wsUrl);
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        url: wsUrl
      });
      wsRef.current = null;
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [currentTaskId]);

  // Валидация файлов
  const validateFiles = useCallback((files: File[]): string | null => {
    // Проверка типа файлов
    const supportedExtensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.dng', '.raw', '.nef', '.cr2', '.arw'];

    for (const file of files) {
      const fileExtension = '.' + file.name.toLowerCase().split('.').pop();
      const hasValidExtension = supportedExtensions.includes(fileExtension);
      const hasValidMimeType = file.type.startsWith('image/') || SUPPORTED_IMAGE_TYPES.includes(file.type);

      if (!hasValidExtension && !hasValidMimeType) {
        return `Файл "${file.name}" не является изображением. Разрешены только изображения.`;
      }
    }

    // Проверка размера
    const currentTotalSize = selectedFiles.reduce((sum, f) => sum + f.file.size, 0);
    const newFilesSize = files.reduce((sum, f) => sum + f.size, 0);
    const totalSize = currentTotalSize + newFilesSize;

    if (totalSize > MAX_SIZE_BYTES) {
      const totalSizeGB = (totalSize / (1024 * 1024 * 1024)).toFixed(2);
      return `Суммарный размер файлов (${totalSizeGB} ГБ) превышает максимально допустимый размер 10 ГБ.`;
    }

    return null;
  }, [selectedFiles]);

  // Создание превью для файла
  const createPreview = useCallback((file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }, []);

  // Создание превью для конкретного файла (ленивая загрузка)
  const loadPreview = useCallback(async (fileWithPreview: FileWithPreview) => {
    if (fileWithPreview.preview) {
      return; // Превью уже создано
    }

    try {
      const preview = await createPreview(fileWithPreview.file);
      setSelectedFiles((prev) =>
        prev.map((f) =>
          f.id === fileWithPreview.id ? { ...f, preview } : f
        )
      );
    } catch (error) {
      console.error('Error creating preview:', error);
    }
  }, [createPreview]);

  // Обработка добавления файлов (без создания превью сразу)
  const addFiles = useCallback((files: File[]) => {
    const validationError = validateFiles(files);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);

    // Создаем файлы БЕЗ превью (ленивая загрузка)
    const filesWithPreviews: FileWithPreview[] = files.map((file) => ({
      file,
      preview: null,
      id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
    }));

    setSelectedFiles((prev) => [...prev, ...filesWithPreviews]);

    // Создаем превью только для первых 20 файлов (для быстрого отображения)
    const filesToPreview = filesWithPreviews.slice(0, 20);
    filesToPreview.forEach((fileWithPreview) => {
      loadPreview(fileWithPreview);
    });
  }, [validateFiles, loadPreview]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      await addFiles(files);
    }
    // Сбрасываем input для возможности повторной загрузки тех же файлов
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDrop = async (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
      await addFiles(files);
    }
  };

  // Удаление файла
  const removeFile = useCallback((id: string) => {
    setSelectedFiles((prev) => {
      const newFiles = prev.filter((f) => f.id !== id);
      // Если удаляем текущее изображение, закрываем просмотр или переключаемся на следующее
      if (selectedImageForView?.id === id) {
        const currentIndex = prev.findIndex(f => f.id === id);
        if (newFiles.length > 0) {
          const nextIndex = currentIndex < newFiles.length ? currentIndex : newFiles.length - 1;
          setSelectedImageForView(newFiles[nextIndex]);
          setSelectedImageIndex(nextIndex);
        } else {
          setSelectedImageForView(null);
          setSelectedImageIndex(null);
        }
      }
      return newFiles;
    });
    setError(null);
  }, [selectedImageForView]);


  // Открытие изображения для просмотра
  const openImageForView = useCallback((file: FileWithPreview, index: number) => {
    setSelectedImageForView(file);
    setSelectedImageIndex(index);
    if (!file.preview) {
      loadPreview(file);
    }
  }, [loadPreview]);


  // Очистка всех файлов
  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  // Валидация перед анализом
  const validateBeforeAnalysis = useCallback((): string | null => {
    if (selectedFiles.length === 0) {
      return "Пожалуйста, загрузите хотя бы одно изображение";
    }

    const totalSize = selectedFiles.reduce((sum, f) => sum + f.file.size, 0);
    if (totalSize > MAX_SIZE_BYTES) {
      const totalSizeGB = (totalSize / (1024 * 1024 * 1024)).toFixed(2);
      return `Суммарный размер файлов (${totalSizeGB} ГБ) превышает максимально допустимый размер 10 ГБ.`;
    }

    return null;
  }, [selectedFiles]);

  const analyzeImages = async () => {
    const validationError = validateBeforeAnalysis();
    if (validationError) {
      setError(validationError);
      return;
    }

    if (selectedFiles.length === 0) return;

    setLoading(true);
    setError(null);
    setAnalysisProgress(null);

    try {
      const formData = new FormData();
      selectedFiles.forEach((fileWithPreview) => {
        formData.append("files", fileWithPreview.file);
      });

      // Формируем URL с параметрами
      let url = `/predict/batch?conf=${confidenceThreshold}`;
      if (routeName.trim()) {
        url += `&route_name=${encodeURIComponent(routeName.trim())}`;
      }

      const response = await apiClient.post(
        url,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 300000, // 5 минут для batch обработки
        }
      );

      // Для batch API возвращается task_id, подключаемся к WebSocket
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
        // WebSocket подключение произойдет автоматически через useEffect
      } else {
        // Если это не batch API, показываем ошибку
        setError('Ожидается batch API с task_id');
        setLoading(false);
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || "Ошибка при обработке изображений"
      );
      console.error("Error:", err);
      setLoading(false);
    }
  };



  // Вычисляем общий размер файлов
  const totalSize = useMemo(() => {
    return selectedFiles.reduce((sum, f) => sum + f.file.size, 0);
  }, [selectedFiles]);

  const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(2);
  const totalSizeGB = (totalSize / (1024 * 1024 * 1024)).toFixed(2);

  // Если открыт просмотр - показываем только просмотр
  if (selectedImageForView && selectedImageIndex !== null) {
    return (
      <div
        className="h-full flex flex-col"
        style={{ padding: '34px 96px 64px' }}
      >
        {/* Список миниатюр для навигации */}
        {selectedFiles.length > 0 && (() => {
          const itemWidth = 38;
          const itemGap = 16;
          const maxWidth = 528;
          const calculatedWidth = selectedFiles.length * itemWidth + (selectedFiles.length - 1) * itemGap;
          const containerWidth = Math.min(calculatedWidth, maxWidth);
          const containerHeight = 38;

          return (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative"
            >
              {/* Список миниатюр по центру */}
              <div className="flex justify-center ">
                <div style={{ maxWidth: `${maxWidth}px`, width: `${containerWidth}px` }}>
                  <div className="pb-4">
                    <div
                      className="no-scroll"
                      style={{
                        height: `${containerHeight}px`,
                        width: `${containerWidth}px`,
                        overflowX: selectedFiles.length > 10 ? 'auto' : 'hidden',
                        overflowY: 'hidden',
                        scrollbarWidth: 'none',
                        msOverflowStyle: 'none',
                      }}
                    >
                      <Virtuoso
                        data={selectedFiles}
                        totalCount={selectedFiles.length}
                        style={{
                          height: `${containerHeight}px`,
                          width: '100%',
                        }}
                        horizontalDirection
                        itemContent={(index) => {
                          const fileWithPreview = selectedFiles[index];
                          if (!fileWithPreview.preview) {
                            setTimeout(() => loadPreview(fileWithPreview), 0);
                          }
                          return (
                            <div
                              style={{
                                width: '38px',
                                height: '38px',
                                marginRight: '16px',
                                flexShrink: 0,
                                display: 'inline-block',
                              }}
                            >
                              <div
                                className={`relative w-[38px] h-[38px] overflow-hidden cursor-pointer hover:opacity-80 transition-all bg-white/10 flex items-center justify-center ${
                                  selectedImageIndex === index ? 'ring-2 ring-white ring-offset-2 ring-offset-transparent' : ''
                                }`}
                                style={{ borderRadius: '8px' }}
                                onClick={() => openImageForView(fileWithPreview, index)}
                              >
                                {fileWithPreview.preview ? (
                                  <img
                                    src={fileWithPreview.preview}
                                    alt={fileWithPreview.file.name}
                                    className="w-full h-full object-cover"
                                    loading="lazy"
                                    onError={() => {
                                      loadPreview(fileWithPreview);
                                    }}
                                  />
                                ) : (
                                  <div className="text-white/40 text-xs text-center px-1">
                                    {index + 1}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
              {/* Кнопка удаления в правом верхнем углу */}
              {selectedImageForView && (
                <button
                  onClick={() => removeFile(selectedImageForView.id)}
                  className="absolute top-1 right-0 z-10 h-[max-content] w-[max-content]"
                  style={{ right: '-50px' }}
                  aria-label="Удалить"
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
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              )}
            </motion.div>
          );
        })()}

        {/* Просмотр фотки */}
        <div className="flex-1 relative flex items-center justify-center">
          {/* Изображение */}
          {selectedImageForView.preview ? (
            <img
              src={selectedImageForView.preview}
              alt={selectedImageForView.file.name}
              className="max-w-full max-h-full object-contain rounded-lg mt-[-70px]"
            />
          ) : (
            <div className="flex items-center justify-center text-white/60">
              Загрузка изображения...
            </div>
          )}

          {/* Информация о файле внизу */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-black/60 backdrop-blur-sm">
            <p className="text-white text-xl font-medium truncate text-center">
              {selectedImageForView.file.name}
            </p>
            <div className="flex items-center justify-center gap-4 mt-2">
              <p className="text-white/60 text-base">
                {(selectedImageForView.file.size / (1024 * 1024)).toFixed(2)} МБ
              </p>
              <p className="text-white/60 text-base">
                {selectedImageIndex + 1} / {selectedFiles.length}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Состояние загрузки файлов (drag&drop)
  return (
    <div
      className="h-full flex flex-col"
      style={{ padding: selectedFiles.length > 0 ? '34px 96px 64px' : '128px 96px' }}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key="upload"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.3 }}
          className="w-full h-full flex flex-col gap-6"
        >
            {/* Загруженные изображения над drag and drop */}
            {selectedFiles.length > 0 && (() => {
              const itemWidth = 38;
              const itemGap = 16;
              const maxWidth = 528;
              const calculatedWidth = selectedFiles.length * itemWidth + (selectedFiles.length - 1) * itemGap;
              const containerWidth = Math.min(calculatedWidth, maxWidth);
              const containerHeight = 38;

              return (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ maxWidth: `${maxWidth}px`, width: `${containerWidth}px`, margin: '0 auto' }}
              >
                <div className="pb-4">
                  <div
                    className="no-scroll"
                    style={{
                      height: `${containerHeight}px`,
                      width: `${containerWidth}px`,
                      overflowX: selectedFiles.length > 10 ? 'auto' : 'hidden',
                      overflowY: 'hidden',
                      scrollbarWidth: 'none',
                      msOverflowStyle: 'none',
                    }}
                  >
                    <Virtuoso
                      data={selectedFiles}
                      totalCount={selectedFiles.length}
                      style={{
                        height: `${containerHeight}px`,
                        width: '100%',
                      }}
                      horizontalDirection
                      itemContent={(index) => {
                      const fileWithPreview = selectedFiles[index];

                      // Загружаем превью для видимых элементов
                      if (!fileWithPreview.preview) {
                        setTimeout(() => loadPreview(fileWithPreview), 0);
                      }

                      return (
                        <div
                          style={{
                            width: '38px',
                            height: '38px',
                            marginRight: '16px',
                            flexShrink: 0,
                            display: 'inline-block',
                          }}
                        >
                          <div
                            className={`relative overflow-hidden cursor-pointer hover:opacity-80 transition-all bg-white/10 flex items-center justify-center ${
                              selectedImageIndex === index ? 'ring-2 ring-white ring-offset-2 ring-offset-transparent' : ''
                            }`}
                            style={{
                              borderRadius: '8px',
                              width: selectedImageIndex === index ? '48px' : '38px',
                              height: selectedImageIndex === index ? '48px' : '38px',
                            }}
                            onClick={() => openImageForView(fileWithPreview, index)}
                          >
                            {fileWithPreview.preview ? (
                              <img
                                src={fileWithPreview.preview}
                                alt={fileWithPreview.file.name}
                                className="w-full h-full object-cover"
                                loading="lazy"
                                onError={() => {
                                  loadPreview(fileWithPreview);
                                }}
                              />
                            ) : (
                              <div className="text-white/40 text-xs text-center px-1">
                                {index + 1}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    }}
                    />
                  </div>
                </div>
              </motion.div>
              );
            })()}

            {/* Drop Zone */}
            <div
              className={`relative border-2 border-dashed rounded-2xl text-center transition-all duration-300 flex-1 flex items-center justify-center ${
                loading || analysisProgress
                  ? "border-white/20 bg-white/5 cursor-not-allowed opacity-50"
                  : isDragging
                  ? "border-white bg-white/5 scale-[1.01] cursor-pointer"
                  : "border-white/30 hover:border-white/50 hover:bg-white/5 cursor-pointer"
              }`}
              style={{
                padding: selectedFiles.length > 0
                  ? '48px 96px 48px 96px'  // Когда загружены документы
                  : '134px 96px 170px 96px'  // До загрузки данных
              }}
              onDragOver={(e) => {
                if (loading || analysisProgress) return;
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => {
                if (loading || analysisProgress) return;
                setIsDragging(false);
              }}
              onDrop={(e) => {
                if (loading || analysisProgress) return;
                handleDrop(e);
              }}
              onClick={() => {
                if (loading || analysisProgress) return;
                fileInputRef.current?.click();
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                accept="image/jpeg,image/jpg,image/png,image/tiff,image/tif,image/bmp,image/dng,image/raw,image/nef,image/cr2,image/arw"
                className="hidden"
              />

              {selectedFiles.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center gap-[24px]"
                >
                  {/* Иконка папки с плюсом или лоадер */}
                  <div className="relative">
                    {loading || analysisProgress ? (
                      <AnalysisLoader />
                    ) : (
                      <img
                        src="/images/new-folder.svg"
                        alt="new-folder"
                      />
                    )}
                  </div>

                  <div className="flex flex-col items-center gap-[10px]">
                    {/* Заголовок */}
                    {!(loading || analysisProgress) && (
                      <h2 className="text-3xl font-bold text-white">
                        Загрузите данные
                      </h2>
                    )}

                    {/* Описание */}
                    <p className="text-white/70 text-base max-w-md leading-tight w-[300px]">
                      Добавьте изображения или <br/>
                      кадры дрона, и LineGuard AI <br />
                      выполнит детальный анализ <br />
                      состояния электросетей
                    </p>
                  </div>

                  {/* Кнопка загрузки */}
                  {!(loading || analysisProgress) && (
                    <Button
                      className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] border border-white/60"
                      style={{ padding: '11px 12.5px', fontWeight: 550 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current?.click();
                      }}
                    >
                      <img src="/images/plus.svg" alt="plus" className="mr-2" />
                      <p className="text-base font-medium">
                        {selectedFiles.length > 0 ? 'Доприкрепить файлы' : 'Прикрепить файлы'}
                      </p>
                    </Button>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center gap-4"
                >
                  <div className="relative">
                    {loading || analysisProgress ? (
                      <AnalysisLoader />
                    ) : (
                      <img
                        src="/images/new-folder.svg"
                        alt="new-folder"
                      />
                    )}
                  </div>

                  {!(loading || analysisProgress) && (
                    <p className="text-xl font-semibold text-white">
                      Загружено {selectedFiles.length} {selectedFiles.length === 1 ? 'изображение' : selectedFiles.length < 5 ? 'изображения' : 'изображений'}
                    </p>
                  )}
                  {analysisProgress && (
                    <div className="space-y-1">
                      <p className="text-white/80 text-sm">
                        Обработано: {analysisProgress.processed_files} / {analysisProgress.total_files}
                      </p>
                      {analysisProgress.total_files > 0 && (
                        <p className="text-white/60 text-xs">
                          Осталось: {analysisProgress.total_files - analysisProgress.processed_files} файлов
                          {analysisProgress.failed_files > 0 && ` · Ошибок: ${analysisProgress.failed_files}`}
                        </p>
                      )}
                      {analysisProgress.defects_found > 0 && (
                        <p className="text-white/60 text-xs">
                          Найдено дефектов: {analysisProgress.defects_found}
                        </p>
                      )}
                    </div>
                  )}
                  {!(loading || analysisProgress) && (
                    <>
                      <p className="text-white/60">
                        Размер: {totalSizeGB >= '1' ? `${totalSizeGB} ГБ` : `${totalSizeMB} МБ`}
                      </p>
                      <div className="flex gap-4 mt-4">
                        <Button
                          className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] border border-white/60"
                          style={{ padding: '11px 12.5px', fontWeight: 550 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            fileInputRef.current?.click();
                          }}
                        >
                          <img src="/images/plus.svg" alt="plus" className="mr-2" />
                          <p className="text-base font-medium">
                            Дозагрузить файлы
                          </p>
                        </Button>
                        <Button
                          className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] border border-white/60"
                          style={{ padding: '11px 12.5px', fontWeight: 550 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            clearFiles();
                          }}
                        >
                          <p className="text-base font-medium">
                            Очистить
                          </p>
                        </Button>
                      </div>
                    </>
                  )}
                </motion.div>
              )}
            </div>

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

            {/* Поле ввода названия маршрута и кнопка "Начать анализ" */}
            {selectedFiles.length > 0 && !loading && !analysisProgress && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 flex flex-col items-center gap-4"
              >
                <div className="w-full max-w-md">
                  <input
                    type="text"
                    value={routeName}
                    onChange={(e) => setRouteName(e.target.value.slice(0, 250))}
                    placeholder="Название маршрута (необязательно, до 250 символов)"
                    className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:border-white/40 transition-colors"
                    maxLength={250}
                  />
                  <p className="text-white/40 text-xs mt-1 text-right">
                    {routeName.length} / 250
                  </p>
                </div>
                <Button
                  size="lg"
                  className="text-white font-bold text-lg rounded-full hover:scale-105 transition-all duration-300 flex items-center justify-center border border-white/60 h-[42px]"
                  radius="full"
                  style={{
                    padding: '13px 12px',
                    backgroundColor: 'rgba(88, 75, 255, 0.4)',
                    fontWeight: 400
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    analyzeImages();
                  }}
                  disabled={loading || selectedFiles.length === 0}
                >
                  <img src="/images/ai-point.svg" alt="AI Point" />
                  Начать анализ
                </Button>
              </motion.div>
            )}
          </motion.div>
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

