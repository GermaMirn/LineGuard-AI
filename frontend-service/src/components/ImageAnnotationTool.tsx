import { useState, useRef, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@heroui/react';

interface BBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
}

interface ImageAnnotationToolProps {
  imageUrl: string;
  imageId: string;
  taskId: string;
  fileId: string; // file_id из result_url или original_url
  projectId: string; // project_id для сохранения файла
  onClose: () => void;
  onSave?: (bboxes: BBox[]) => void;
}

export default function ImageAnnotationTool({
  imageUrl,
  imageId,
  taskId,
  fileId,
  projectId,
  onClose,
  onSave,
}: ImageAnnotationToolProps) {
  const [bboxes, setBboxes] = useState<BBox[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentBBox, setCurrentBBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const startPosRef = useRef<{ x: number; y: number } | null>(null);

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
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(bbox.x, bbox.y, bbox.width, bbox.height);
        
        // Рисуем метку если есть
        if (bbox.label) {
          ctx.fillStyle = '#EF4444';
          ctx.font = '14px Arial';
          ctx.fillText(bbox.label, bbox.x, bbox.y - 5);
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
      setBboxes([...bboxes, newBBox]);
    }

    setIsDrawing(false);
    setCurrentBBox(null);
    startPosRef.current = null;
  }, [isDrawing, currentBBox, bboxes]);

  const handleDeleteBBox = useCallback((id: string) => {
    setBboxes(bboxes.filter((bbox) => bbox.id !== id));
  }, [bboxes]);

  const handleSave = async () => {
    if (bboxes.length === 0) {
      alert('Добавьте хотя бы одну область для выделения');
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
      }));

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

      alert('Области успешно сохранены!');
      onClose();
    } catch (error) {
      console.error('Error saving annotations:', error);
      alert('Не удалось сохранить области');
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
          <Button
            onClick={handleSave}
            disabled={isSaving || bboxes.length === 0}
            className="bg-green-500 hover:bg-green-600 text-white"
            size="sm"
          >
            {isSaving ? 'Сохранение...' : 'Сохранить'}
          </Button>
          <Button
            onClick={onClose}
            className="bg-gray-500 hover:bg-gray-600 text-white"
            size="sm"
          >
            Отмена
          </Button>
          <Button
            onClick={() => setBboxes([])}
            disabled={bboxes.length === 0}
            className="bg-red-500 hover:bg-red-600 text-white"
            size="sm"
          >
            Очистить все
          </Button>
        </div>

        {/* Информация о количестве bbox */}
        <div className="absolute top-4 right-4 z-20 bg-black/60 backdrop-blur-sm rounded-lg p-2 text-white text-sm">
          Выделено областей: {bboxes.length}
        </div>

        {/* Контейнер с изображением и canvas */}
        <div
          ref={containerRef}
          className="flex-1 flex items-center justify-center overflow-auto p-4"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{ cursor: isDrawing ? 'crosshair' : 'default' }}
        >
          <div className="relative inline-block">
            <img
              ref={imageRef}
              src={imageUrl}
              alt="Annotation"
              className="max-w-full max-h-full object-contain"
              draggable={false}
            />
            <canvas
              ref={canvasRef}
              className="absolute top-0 left-0 pointer-events-none"
              style={{ maxWidth: '100%', maxHeight: '100%' }}
            />
          </div>
        </div>

        {/* Инструкция */}
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20 bg-black/60 backdrop-blur-sm rounded-lg p-3 text-white text-sm text-center">
          Зажмите левую кнопку мыши и перетащите для выделения области
        </div>
      </motion.div>
    </div>
  );
}

