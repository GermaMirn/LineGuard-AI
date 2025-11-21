import { useState, useRef, useCallback, useEffect, memo } from 'react';
import { motion } from 'framer-motion';

interface BBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  name?: string;
  is_defect?: boolean; // true = повреждение, false = нормальный объект
}

interface ImageAnnotationToolProps {
  imageUrl: string;
  imageId: string;
  taskId: string;
  fileId: string; // file_id из result_url или original_url
  projectId: string; // project_id для сохранения файла
  onClose: () => void;
  onSave?: (bboxes: BBox[]) => void;
  onImageUpdated?: () => void; // Callback для обновления изображения после сохранения
  existingDetections?: Array<{
    bbox: number[];
    class_ru?: string;
    class?: string;
    is_manual?: boolean;
  }>; // Существующие детекции для загрузки ручных аннотаций
}

function ImageAnnotationTool({
  imageUrl,
  imageId,
  taskId,
  fileId,
  projectId,
  onClose,
  onSave,
  onImageUpdated,
  existingDetections = [],
}: ImageAnnotationToolProps) {
  const [bboxes, setBboxes] = useState<BBox[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentBBox, setCurrentBBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [editingBBoxId, setEditingBBoxId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string>('');
  const [editingIsDefect, setEditingIsDefect] = useState<boolean>(true); // По умолчанию повреждение
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const startPosRef = useRef<{ x: number; y: number } | null>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Загружаем существующие ручные аннотации при открытии инструмента
  useEffect(() => {
    if (existingDetections && existingDetections.length > 0) {
      const image = imageRef.current;
      if (!image) return;

      // Ждем загрузки изображения
      const loadExistingAnnotations = () => {
        const imageWidth = image.naturalWidth;
        const imageHeight = image.naturalHeight;
        const displayWidth = image.offsetWidth;
        const displayHeight = image.offsetHeight;

        const existingBboxes: BBox[] = existingDetections
          .filter((detection) => detection.is_manual)
          .map((detection) => {
            const bbox = detection.bbox || [];
            if (bbox.length !== 4) return null;

            // Преобразуем из абсолютных координат [x1, y1, x2, y2] в относительные [x, y, width, height]
            const [x1, y1, x2, y2] = bbox;
            const width = x2 - x1;
            const height = y2 - y1;

            // Конвертируем обратно в координаты отображения
            const x = (x1 / imageWidth) * displayWidth;
            const y = (y1 / imageHeight) * displayHeight;
            const displayWidth_scaled = (width / imageWidth) * displayWidth;
            const displayHeight_scaled = (height / imageHeight) * displayHeight;

            const result: BBox = {
              id: `existing-${Date.now()}-${Math.random()}`,
              x: Math.round(x),
              y: Math.round(y),
              width: Math.round(displayWidth_scaled),
              height: Math.round(displayHeight_scaled),
              is_defect: true, // По умолчанию, можно улучшить, если есть defect_summary
            };

            if (detection.class_ru || detection.class) {
              result.name = detection.class_ru || detection.class;
            }

            return result;
          })
          .filter((bbox): bbox is BBox => bbox !== null);

        if (existingBboxes.length > 0) {
          console.log('📥 Загружено существующих аннотаций:', existingBboxes.length);
          setBboxes(existingBboxes);
        }
      };

      if (image.complete && image.naturalWidth > 0 && image.naturalHeight > 0) {
        loadExistingAnnotations();
      } else {
        const handleLoad = () => {
          if (image.naturalWidth > 0 && image.naturalHeight > 0) {
            loadExistingAnnotations();
          }
        };
        image.addEventListener('load', handleLoad);
        return () => {
          image.removeEventListener('load', handleLoad);
        };
      }
    }
  }, [existingDetections, imageUrl]);

  // Загружаем изображение и рисуем bbox на canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    if (!canvas || !image) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      // Очищаем canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Рисуем все сохраненные bbox
      bboxes.forEach((bbox) => {
        const isDefect = bbox.is_defect !== false; // По умолчанию true
        ctx.strokeStyle = isDefect ? '#EF4444' : '#10B981'; // Красный для дефекта, зеленый для нормы
        ctx.lineWidth = 2;
        ctx.strokeRect(bbox.x, bbox.y, bbox.width, bbox.height);

        // Рисуем название если есть
        if (bbox.name) {
          const bgColor = isDefect ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)'; // Красный для дефекта, зеленый для нормы

          ctx.font = 'bold 14px Arial';
          const text = bbox.name;
          const textMetrics = ctx.measureText(text);
          const textWidth = textMetrics.width;
          const textHeight = 16;

          // Рисуем фон для текста
          ctx.fillStyle = bgColor;
          ctx.fillRect(bbox.x, bbox.y - textHeight - 2, textWidth + 8, textHeight + 4);

          // Рисуем текст
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(text, bbox.x + 4, bbox.y - 5);
        }
      });

      // Рисуем текущий bbox который рисуется
      if (currentBBox) {
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(currentBBox.x, currentBBox.y, currentBBox.width, currentBBox.height);
        ctx.setLineDash([]);
      }
    };

    draw();
  }, [bboxes, currentBBox]);

  // Обновляем размер canvas при изменении размера изображения
  useEffect(() => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    if (!canvas || !image) return;

    const updateCanvasSize = () => {
      canvas.width = image.offsetWidth;
      canvas.height = image.offsetHeight;
    };

    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    return () => window.removeEventListener('resize', updateCanvasSize);
  }, [imageUrl]);

  const getRelativeCoordinates = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const container = containerRef.current;
    const image = imageRef.current;
    if (!container || !image) return null;

    const rect = container.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();

    const x = e.clientX - imageRect.left;
    const y = e.clientY - imageRect.top;

    return { x, y };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return; // Только левая кнопка мыши

    const coords = getRelativeCoordinates(e);
    if (!coords) return;

    setIsDrawing(true);
    startPosRef.current = coords;
    setCurrentBBox({ x: coords.x, y: coords.y, width: 0, height: 0 });
  }, [getRelativeCoordinates]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !startPosRef.current) return;

    const coords = getRelativeCoordinates(e);
    if (!coords) return;

    const width = coords.x - startPosRef.current.x;
    const height = coords.y - startPosRef.current.y;

    setCurrentBBox({
      x: Math.min(startPosRef.current.x, coords.x),
      y: Math.min(startPosRef.current.y, coords.y),
      width: Math.abs(width),
      height: Math.abs(height),
    });
  }, [isDrawing, getRelativeCoordinates]);

  const handleMouseUp = useCallback(() => {
    if (!isDrawing || !currentBBox || !startPosRef.current) return;

    // Сохраняем bbox только если он достаточно большой
    if (currentBBox.width > 10 && currentBBox.height > 10) {
      const newBBox: BBox = {
        id: `bbox-${Date.now()}`,
        x: currentBBox.x,
        y: currentBBox.y,
        width: currentBBox.width,
        height: currentBBox.height,
      };
      // Временно добавляем bbox в список (будет удален при отмене)
      setBboxes([...bboxes, newBBox]);
      // Открываем диалог для ввода названия и выбора типа
      setEditingBBoxId(newBBox.id);
      setEditingName('');
      setEditingIsDefect(true); // По умолчанию повреждение
    }

    setIsDrawing(false);
    setCurrentBBox(null);
    startPosRef.current = null;
  }, [isDrawing, currentBBox, bboxes]);

  const handleDeleteBBox = useCallback((id: string) => {
    setBboxes(bboxes.filter((bbox) => bbox.id !== id));
    if (editingBBoxId === id) {
      setEditingBBoxId(null);
      setEditingName('');
    }
  }, [bboxes, editingBBoxId]);

  const handleSaveName = useCallback(() => {
    if (!editingBBoxId) return;

    setBboxes(bboxes.map(bbox =>
      bbox.id === editingBBoxId
        ? { ...bbox, name: editingName.trim() || undefined, is_defect: editingIsDefect }
        : bbox
    ));
    setEditingBBoxId(null);
    setEditingName('');
    setEditingIsDefect(true);
  }, [editingBBoxId, editingName, editingIsDefect, bboxes]);

  const handleCancelEdit = useCallback(() => {
    // Удаляем bbox из списка при отмене
    if (editingBBoxId) {
      setBboxes(bboxes.filter(bbox => bbox.id !== editingBBoxId));
    }
    setEditingBBoxId(null);
    setEditingName('');
    setEditingIsDefect(true);
  }, [editingBBoxId, bboxes]);

  const handleSave = async () => {
    if (bboxes.length === 0) {
      // Не показываем alert, просто не сохраняем
      return;
    }

    setIsSaving(true);
    try {
      const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";

      // Получаем размеры изображения для нормализации координат
      const image = imageRef.current;
      if (!image) return;

      const imageWidth = image.naturalWidth;
      const imageHeight = image.naturalHeight;
      const displayWidth = image.offsetWidth;
      const displayHeight = image.offsetHeight;

      // Нормализуем координаты относительно реального размера изображения
      const normalizedBboxes = bboxes.map((bbox) => ({
        x: Math.round((bbox.x / displayWidth) * imageWidth),
        y: Math.round((bbox.y / displayHeight) * imageHeight),
        width: Math.round((bbox.width / displayWidth) * imageWidth),
        height: Math.round((bbox.height / displayHeight) * imageHeight),
        name: bbox.name || undefined,
        is_defect: bbox.is_defect !== false, // По умолчанию true
      }));

      // Логируем для отладки
      console.log('💾 Сохранение аннотаций:', {
        totalBboxes: normalizedBboxes.length,
        bboxes: normalizedBboxes.map(b => ({
          name: b.name,
          x: b.x,
          y: b.y,
          width: b.width,
          height: b.height,
          is_defect: b.is_defect
        }))
      });

      const response = await fetch(
        `${BFF_SERVICE_URL}/analysis/tasks/${taskId}/images/${imageId}/annotate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_id: fileId,
            bboxes: normalizedBboxes,
            project_id: projectId,
            file_type: 'ANALYSIS_RESULT',
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to save annotations');
      }

      if (onSave) {
        onSave(bboxes);
      }

      // Закрываем модалку сразу
      onClose();

      // Уведомляем о обновлении изображения с небольшой задержкой
      // чтобы дать время базе данных сохранить изменения
      if (onImageUpdated) {
        setTimeout(() => {
          onImageUpdated();
        }, 500);
      }
    } catch (error) {
      console.error('Error saving annotations:', error);
      // Не показываем alert, просто логируем ошибку
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative w-full h-full flex flex-col"
      >
        {/* Панель инструментов */}
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20 flex gap-2 bg-black/60 backdrop-blur-sm rounded-lg p-2">
          <button
            onClick={handleSave}
            disabled={isSaving || bboxes.length === 0}
            className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              padding: '11px 12.5px',
              fontWeight: 550,
              backgroundColor: 'rgba(16, 185, 129, 0.3)',
              border: '1px solid rgba(16, 185, 129, 0.5)',
              boxShadow: 'inset 0 2px 8px rgba(16, 185, 129, 0.3), inset 0 1px 3px rgba(16, 185, 129, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.2)',
            }}
            onMouseEnter={(e) => {
              if (!isSaving && bboxes.length > 0) {
                e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.4)';
                e.currentTarget.style.boxShadow = 'inset 0 2px 10px rgba(16, 185, 129, 0.4), inset 0 1px 4px rgba(16, 185, 129, 0.3), inset 0 -1px 0 rgba(0, 0, 0, 0.2)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.3)';
              e.currentTarget.style.boxShadow = 'inset 0 2px 8px rgba(16, 185, 129, 0.3), inset 0 1px 3px rgba(16, 185, 129, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.2)';
            }}
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
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            {isSaving ? 'Сохранение...' : 'Сохранить'}
          </button>
          <button
            onClick={() => setBboxes([])}
            disabled={bboxes.length === 0}
            className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              padding: '11px 12.5px',
              fontWeight: 550,
              backgroundColor: 'rgba(239, 68, 68, 0.3)',
              border: '1px solid rgba(239, 68, 68, 0.5)',
              boxShadow: 'inset 0 2px 8px rgba(239, 68, 68, 0.3), inset 0 1px 3px rgba(239, 68, 68, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.2)',
            }}
            onMouseEnter={(e) => {
              if (bboxes.length > 0) {
                e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.4)';
                e.currentTarget.style.boxShadow = 'inset 0 2px 10px rgba(239, 68, 68, 0.4), inset 0 1px 4px rgba(239, 68, 68, 0.3), inset 0 -1px 0 rgba(0, 0, 0, 0.2)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.3)';
              e.currentTarget.style.boxShadow = 'inset 0 2px 8px rgba(239, 68, 68, 0.3), inset 0 1px 3px rgba(239, 68, 68, 0.2), inset 0 -1px 0 rgba(0, 0, 0, 0.2)';
            }}
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
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            Очистить все
          </button>
                    <button
            onClick={onClose}
            className="text-white rounded-[8px] whitespace-nowrap flex items-center justify-center gap-[4px] border border-white/60 transition-all hover:bg-white/10"
            style={{ padding: '11px 12.5px', fontWeight: 550 }}
          >
            Отмена
          </button>
        </div>

        {/* Информация о количестве bbox */}
        <div className="absolute top-4 right-4 z-20 bg-black/60 backdrop-blur-sm rounded-lg p-2 text-white text-sm">
          Выделено областей: {bboxes.length}
        </div>

        {/* Контейнер с изображением и canvas */}
        <div
          ref={containerRef}
          className="flex-1 flex items-center justify-center overflow-auto p-4 relative"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{ cursor: isDrawing ? 'crosshair' : 'default' }}
        >
          {/* Затемнение справа */}
          <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-black/40 to-transparent pointer-events-none z-10" />

          <div className="relative inline-block">
            <img
              key={`annotation-${imageUrl}`}
              ref={imageRef}
              src={imageUrl}
              alt="Annotation"
              className="max-w-full max-h-full object-contain"
              draggable={false}
              onLoad={() => {
                // Перерисовываем canvas после загрузки изображения
                const canvas = canvasRef.current;
                const image = imageRef.current;
                if (!canvas || !image) return;

                const ctx = canvas.getContext('2d');
                if (!ctx) return;

                // Обновляем размер canvas под размер изображения
                canvas.width = image.offsetWidth;
                canvas.height = image.offsetHeight;

                // Перерисовываем bboxes
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                bboxes.forEach((bbox) => {
                  const isDefect = bbox.is_defect !== false; // По умолчанию true
                  ctx.strokeStyle = isDefect ? '#EF4444' : '#10B981'; // Красный для дефекта, зеленый для нормы
                  ctx.lineWidth = 2;
                  ctx.strokeRect(bbox.x, bbox.y, bbox.width, bbox.height);
                  if (bbox.name) {
                    const bgColor = isDefect ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)';
                    ctx.fillStyle = bgColor;
                    ctx.font = 'bold 14px Arial';
                    const text = bbox.name;
                    const textMetrics = ctx.measureText(text);
                    const textWidth = textMetrics.width;
                    const textHeight = 16;
                    ctx.fillRect(bbox.x, bbox.y - textHeight - 2, textWidth + 8, textHeight + 4);
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillText(text, bbox.x + 4, bbox.y - 5);
                  }
                });
              }}
            />
            <canvas
              ref={canvasRef}
              className="absolute top-0 left-0 pointer-events-none"
              style={{ maxWidth: '100%', maxHeight: '100%' }}
            />
          </div>
        </div>

        {/* Инструкция */}
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20 bg-black/80 backdrop-blur-sm rounded-lg p-3 text-base text-center" style={{ color: '#FFFFFF' }}>
          Зажмите левую кнопку мыши и перетащите для выделения области
        </div>

        {/* Диалог для ввода названия маски */}
        {editingBBoxId && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/80">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 border border-gray-700"
            >
              <h3 className="text-white text-lg font-semibold mb-4">
                Введите название маски
              </h3>
              <input
                ref={nameInputRef}
                type="text"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSaveName();
                  } else if (e.key === 'Escape') {
                    handleCancelEdit();
                  }
                }}
                placeholder="Например: Поврежденный изолятор"
                className={`w-full px-4 py-2 bg-gray-700 text-white rounded-lg border mb-4 focus:outline-none focus:ring-2 transition-colors ${
                  editingIsDefect
                    ? 'border-gray-600 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-600 focus:border-green-500 focus:ring-green-500'
                }`}
                autoFocus
              />

              {/* Выбор типа объекта */}
              <div className="mb-4">
                <label className="text-white text-sm font-medium mb-2 block">
                  Тип объекта:
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setEditingIsDefect(true)}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                      editingIsDefect
                        ? 'bg-red-500/20 border-red-500 text-red-300'
                        : 'bg-gray-700 border-gray-600 text-white/60 hover:border-gray-500'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <span>Повреждение</span>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingIsDefect(false)}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                      !editingIsDefect
                        ? 'bg-green-500/20 border-green-500 text-green-300'
                        : 'bg-gray-700 border-gray-600 text-white/60 hover:border-gray-500'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Норма</span>
                    </div>
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="text-white rounded-[8px] w-full flex items-center justify-center gap-[4px] transition-all border border-white hover:bg-white/10"
                  style={{
                    padding: '11px 12.5px',
                    fontWeight: 550,
                  }}
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
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  Отмена
                </button>
                <button
                  type="button"
                  onClick={handleSaveName}
                  className="text-white rounded-[8px] w-full flex items-center justify-center gap-[4px] transition-all border border-white hover:bg-white/10"
                  style={{
                    padding: '11px 12.5px',
                    fontWeight: 550,
                  }}
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
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Сохранить
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </motion.div>
    </div>
  );
}

// Экспортируем мемоизированную версию компонента
export default memo(ImageAnnotationTool);

