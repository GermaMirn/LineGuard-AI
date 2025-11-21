import { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import AnalysisContent from "@/components/AnalysisContent";
import HistoryContent from "@/components/HistoryContent";
import AnalysisHistoryContents from "@/components/AnalysisHistoryContents";
import Loader from "@/components/Loader";
import apiClient from "@/shared/api/axios";

interface TaskImageResponse {
  id: string;
  file_id: string;
  file_name: string;
  file_size: number;
  status: string;
  is_preview: boolean;
  summary?: any;
  result_file_id?: string | null;
  error_message?: string | null;
  created_at: string;
  original_url: string;
  result_url?: string | null;
  thumbnail?: string | null;  // base64 thumbnail для оптимизации
}

export default function AnalysisPage() {
  const [searchParams] = useSearchParams();
  const currentModel = searchParams.get('model') || 'analysis';
  const taskId = searchParams.get('task_id');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [processedFilesCount, setProcessedFilesCount] = useState<number>(0);
  const [resultsArchiveFileId, setResultsArchiveFileId] = useState<string | null>(null);
  const [taskImages, setTaskImages] = useState<TaskImageResponse[]>([]);
  const [taskImagesTotal, setTaskImagesTotal] = useState<number>(0);
  const [isViewingImage, setIsViewingImage] = useState(false);
  const [routeName, setRouteName] = useState<string | null>(null);

  const loadTaskData = useCallback(async () => {
    if (!taskId) {
      return;
    }

      try {
        setLoading(true);
        setError(null);

        const [taskResponse, imagesResponse] = await Promise.all([
          apiClient.get(`/analysis/tasks/${taskId}`),
          apiClient.get(`/analysis/tasks/${taskId}/images`, {
            params: {
              skip: 0,
              limit: 50,
              include_thumbnails: true,
            },
          }),
        ]);

        const taskData = taskResponse.data;
        const imagesData = imagesResponse.data as {
          images: TaskImageResponse[];
          total: number;
        };

        // Сохраняем название маршрута
        setRouteName(taskData.route_name || null);

        // Преобразуем данные задачи в формат Results для отображения
        if (taskData.metadata) {
          const metadata = taskData.metadata;
          const resultsData = {
            total_objects: metadata.total_objects || 0,
            defects_count: metadata.defects_found || 0,
            has_defects: (metadata.defects_found || 0) > 0,
            statistics: metadata.class_stats || {},
            detections: [], // Для batch анализа детекции в архиве
          };
          setResults(resultsData);
          setProcessedFilesCount(taskData.processed_files || 0);

          // Сохраняем ID архива с результатами для скачивания
          if (taskData.results_archive_file_id) {
            setResultsArchiveFileId(taskData.results_archive_file_id);
          }
        const loadedImages = imagesData?.images || [];
        setTaskImages(loadedImages);
          setTaskImagesTotal(imagesData?.total || 0);
        
        } else {
          setError("Метаданные задачи не найдены");
        }
      } catch (err: any) {
        console.error("Error loading task data:", err);
        setError(
          err.response?.data?.detail || "Не удалось загрузить данные задачи"
        );
      } finally {
        setLoading(false);
      }
  }, [taskId]);

  useEffect(() => {
    loadTaskData();
  }, [loadTaskData]);

  return (
    <div className="h-screen bg-black text-white flex overflow-hidden relative">
      {/* Декоративные световые элементы */}
      <img
        src="/images/light.svg"
        alt="Light 1"
        className="absolute top-0 left-0 pointer-events-none"
        style={{
          zIndex: 1,
        }}
        loading="eager"
        onError={() => {
          console.error('Failed to load light.svg');
        }}
      />
      <img
        src="/images/light-2.svg"
        alt="Light 2"
        className="absolute bottom-0 right-0 pointer-events-none"
        style={{
          zIndex: 1,
        }}
        loading="eager"
        onError={() => {
          console.error('Failed to load light-2.svg');
        }}
      />

      {/* Левая боковая панель */}
      <div
        className="transition-all duration-300 flex flex-col items-center py-6 w-24 pt-[47px] pb-[47px]"
        style={{ borderRight: '1px solid rgba(255, 255, 255, 0.1)' }}
      >
        {/* Логотип вверху или стрелка назад */}
        {isViewingImage ? (
          <button
            onClick={() => {
              setIsViewingImage(false);
              // Вызываем функцию закрытия просмотра
              if (currentModel === 'analysis' && !taskId) {
                // Для страницы загрузки файлов
                if ((window as any).__closeImageView) {
                  (window as any).__closeImageView();
                }
              } else if (taskId) {
                // Для страницы истории с task_id
                if ((window as any).__closeHistoryImageView) {
                  (window as any).__closeHistoryImageView();
                }
              }
            }}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="Назад"
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
        ) : (
          <img
            src="/images/logo-small.svg"
            alt="LineGuard AI"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        )}

        {/* Пустое пространство для центрирования навигации */}
        <div className="flex-1"></div>

        {/* Навигация по центру вертикали */}
        <div className="flex flex-col items-center gap-8">
          {/* Анализ */}
          <Link
            to="/panel?model=analysis"
            className="flex flex-col items-center gap-2 p-3"
          >
            <img
              src="/images/analysis.svg"
              alt="analysis"
              className={`rounded-full transition-colors p-[8px] ${
                currentModel === 'analysis'
                  ? 'bg-white/10 hover:bg-white/20'
                  : 'hover:bg-white/10'
              }`}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className={`text-xs font-medium ${
              currentModel === 'analysis' ? 'text-white' : 'text-white/60'
            }`}>
              АНАЛИЗ
            </span>
          </Link>

          {/* История */}
          <Link
            to="/panel?model=history"
            className="flex flex-col items-center gap-2 p-3"
          >
            <img
              src="/images/history.svg"
              alt="history"
              className={`rounded-full transition-colors p-[8px] ${
                currentModel === 'history'
                  ? 'bg-white/10 hover:bg-white/20'
                  : 'hover:bg-white/10'
              }`}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className={`text-xs font-medium ${
              currentModel === 'history' ? 'text-white' : 'text-white/60'
            }`}>
              ИСТОРИЯ
            </span>
          </Link>
        </div>

        {/* Пустое пространство для центрирования нижних элементов */}
        <div className="flex-1"></div>

        {/* Нижние элементы */}
        <div className="flex flex-col items-center gap-6">
          {/* Помощь */}
          <button className="p-3 rounded-lg hover:bg-white/10 transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/>
              <path d="M9.09 9C9.3251 8.33167 9.78915 7.76811 10.4 7.40913C11.0108 7.05016 11.7289 6.91894 12.4272 7.03871C13.1255 7.15849 13.7588 7.52152 14.2151 8.06353C14.6713 8.60553 14.9211 9.29152 14.92 10C14.92 12 11.92 13 11.92 13M12 17H12.01" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          {/* Аватар */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <span className="text-white text-sm font-medium">U</span>
          </div>
        </div>
      </div>

      {/* Основная область */}
      <div className="flex-1 relative overflow-auto">
        {taskId ? (
          loading ? (
            <div className="h-full flex items-center justify-center">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center gap-4"
              >
                <Loader />
                <p className="text-white/70 text-lg">Загрузка данных задачи...</p>
              </motion.div>
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-6 bg-red-500/20 border border-red-500/50 rounded-xl max-w-md"
              >
                <p className="text-red-300 font-semibold flex items-center gap-2">
                  <span className="text-2xl">❌</span>
                  <span>Ошибка: {error}</span>
                </p>
              </motion.div>
            </div>
          ) : results ? (
            <AnalysisHistoryContents
              results={results}
              processedFilesCount={processedFilesCount}
              resultsArchiveFileId={resultsArchiveFileId}
              routeName={routeName}
              images={taskImages}
              totalImages={taskImagesTotal}
              taskId={taskId}
              onImageDeleted={(imageId: string) => {
                // Удаляем изображение из локального состояния
                setTaskImages((prevImages) => prevImages.filter((img) => img.id !== imageId));
                setTaskImagesTotal((prev) => prev - 1);
              }}
              onImageUpdated={async () => {
                // Обновляем только конкретное изображение без полной перезагрузки
                if (taskId) {
                  try {
                    const imagesResponse = await apiClient.get(`/analysis/tasks/${taskId}/images`, {
                      params: {
                        skip: 0,
                        limit: 50,
                        include_thumbnails: true,
                      },
                    });
                    const imagesData = imagesResponse.data as {
                      images: TaskImageResponse[];
                      total: number;
                    };
                    setTaskImages(imagesData?.images || []);
                    setTaskImagesTotal(imagesData?.total || 0);
                  } catch (err) {
                    console.error("Error updating image data:", err);
                  }
                }
              }}
              onViewModeChange={setIsViewingImage}
            />
          ) : null
        ) : (
          currentModel === 'analysis' ? (
            <AnalysisContent onViewModeChange={setIsViewingImage} />
          ) : (
            <HistoryContent />
          )
        )}
      </div>
    </div>
  );
}

