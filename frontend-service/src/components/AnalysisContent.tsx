import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Progress } from "@heroui/react";
import { motion, AnimatePresence } from "framer-motion";
import { Virtuoso } from "react-virtuoso";
import apiClient from "@/shared/api/axios";


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

export default function AnalysisContent() {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confidenceThreshold] = useState(0.5);
  const [selectedImageForModal, setSelectedImageForModal] = useState<FileWithPreview | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setSelectedFiles((prev) => prev.filter((f) => f.id !== id));
    setError(null);
  }, []);


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

      const response = await apiClient.post(
        `/predict/batch?conf=${confidenceThreshold}`,
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
                      height: '38px',
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
                        height: '38px',
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
                            className="relative w-[38px] h-[38px] overflow-hidden cursor-pointer hover:opacity-80 transition-opacity bg-white/10 flex items-center justify-center"
                            style={{ borderRadius: '8px' }}
                            onClick={() => setSelectedImageForModal(fileWithPreview)}
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
                      {loading || analysisProgress ? 'Идет анализ...' : 'Загрузите данные'}
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
                  {!(loading || analysisProgress) && (
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
                        {selectedFiles.length > 0 ? 'Дозагрузить файлы' : 'Загрузить данные'}
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
                    <img
                      src="/images/new-folder.svg"
                      alt="new-folder"
                    />
                  </div>

                  <p className="text-xl font-semibold text-white">
                    {loading || analysisProgress
                      ? 'Идет анализ...'
                      : `Загружено ${selectedFiles.length} ${selectedFiles.length === 1 ? 'изображение' : selectedFiles.length < 5 ? 'изображения' : 'изображений'}`
                    }
                  </p>
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
                          className="bg-white text-black rounded-full whitespace-nowrap flex items-center justify-center gap-[4px]"
                          style={{ padding: '7px 16px 11px 16px', fontWeight: 550 }}
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
                          className="bg-white text-black rounded-full whitespace-nowrap flex items-center justify-center gap-[4px]"
                          style={{ padding: '7px 16px 11px 16px', fontWeight: 550 }}
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

            {/* Кнопка "Начать анализ" */}
            {selectedFiles.length > 0 && !loading && !analysisProgress && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 flex justify-center"
              >
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

      {/* Модалка с изображением */}
      <AnimatePresence>
        {selectedImageForModal && (
          <>
            <ModalImagePreview
              fileWithPreview={selectedImageForModal}
              loadPreview={loadPreview}
              onClose={() => setSelectedImageForModal(null)}
            />
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// Компонент модалки с изображением
function ModalImagePreview({
  fileWithPreview,
  loadPreview,
  onClose
}: {
  fileWithPreview: FileWithPreview;
  loadPreview: (file: FileWithPreview) => void;
  onClose: () => void;
}) {
  // Загружаем превью при открытии модалки
  useEffect(() => {
    if (!fileWithPreview.preview) {
      loadPreview(fileWithPreview);
    }
  }, [fileWithPreview, loadPreview]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="relative max-w-7xl max-h-[90vh] bg-black/90 rounded-xl overflow-hidden border border-white/20"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Кнопка закрытия */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-10 h-10 bg-black/60 hover:bg-black/80 rounded-full flex items-center justify-center transition-colors"
          aria-label="Закрыть"
        >
          <span className="text-white text-2xl font-bold">×</span>
        </button>

        {/* Изображение */}
        <div className="p-4">
          {fileWithPreview.preview ? (
            <img
              src={fileWithPreview.preview}
              alt={fileWithPreview.file.name}
              className="max-w-full max-h-[80vh] object-contain mx-auto rounded-lg"
            />
          ) : (
            <div className="flex items-center justify-center h-[400px] text-white/60">
              Загрузка изображения...
            </div>
          )}
        </div>

        {/* Название файла */}
        <div className="px-4 pb-4 text-center">
          <p className="text-white text-sm font-medium truncate max-w-md mx-auto">
            {fileWithPreview.file.name}
          </p>
          <p className="text-white/60 text-xs mt-1">
            {(fileWithPreview.file.size / (1024 * 1024)).toFixed(2)} МБ
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}

