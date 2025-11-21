import { useCallback, useState, useRef, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

interface TaskItemData {
  id: string;
  status: string;
  route_name?: string | null;
  total_files: number;
  processed_files: number;
  defects_found: number;
  created_at: string;
  completed_at?: string | null;
}

interface TaskHistoryContentsProps {
  tasks: TaskItemData[];
  onTaskDeleted?: (taskId: string) => void;
}

interface TaskItemProps {
  task: TaskItemData;
  formatDate: (date: string) => string;
  onOpenTask: (taskId: string) => void;
  onDeleteTask: (taskId: string) => void;
}

function TaskItem({ task, formatDate, onOpenTask, onDeleteTask }: TaskItemProps) {
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

        if (left + menuWidth > window.innerWidth) {
          left = window.innerWidth - menuWidth - 8;
        }

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

  const handleOpenTask = () => {
    // Блокируем переход, если задача в обработке или в очереди
    const status = task.status.toLowerCase();
    if (status === "processing" || status === "queued") {
      return;
    }
    onOpenTask(task.id);
    setIsMenuOpen(false);
  };

  const handleDeleteTask = () => {
    onDeleteTask(task.id);
    setIsMenuOpen(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "/images/status-completed.svg";
      case "processing":
        return "/images/status-processing.svg";
      case "failed":
        return "/images/status-failed.svg";
      case "queued":
        return "/images/status-queued.svg";
      default:
        return "/images/status-queued.svg";
    }
  };

  const getStatusText = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "Обработано";
      case "processing":
        return "В обработке";
      case "failed":
        return "Ошибка";
      case "queued":
        return "В очереди";
      default:
        return status;
    }
  };

  const getStatusTextColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "#34C759";
      case "processing":
        return "#FF8D28";
      case "failed":
        return "#FF3B30";
      case "queued":
        return "#FFCC00";
      default:
        return "#8E8E93";
    }
  };

  const hasDefects = task.defects_found > 0;
  const isProcessing = task.status.toLowerCase() === "processing" || task.status.toLowerCase() === "queued";

  return (
    <div
      className={`grid grid-cols-[minmax(0,300px)_1fr_1fr_1fr_auto] items-center gap-8 p-3.5 bg-white/5 border border-white/10 rounded-2xl transition-colors ${
        isProcessing
          ? "cursor-not-allowed opacity-70"
          : "hover:bg-white/10 cursor-pointer"
      }`}
      onClick={handleOpenTask}
      style={{ paddingLeft: '32px', paddingRight: '32px' }}
    >
      {/* Иконка и название маршрута */}
      <div className="flex items-center gap-4 min-w-0 max-w-[300px]">
        <div className="relative rounded-xl overflow-hidden flex-shrink-0 w-14 h-14 flex items-center justify-center" style={{marginLeft:"-16px"}}>
          <img
            src="/images/default-image.svg"
            alt="task"
            className="w-full h-full object-cover"
          />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-base font-semibold text-white truncate">
            {task.route_name || `Задача #${task.id.slice(0, 8)}`}
          </h4>
          <p className="text-xs text-white/60">
            {formatDate(task.created_at)}
          </p>
        </div>
      </div>

      {/* Статус */}
      <div className="flex items-center justify-center gap-2">
        <img
          src={getStatusIcon(task.status)}
          alt={getStatusText(task.status)}
          className="w-6 h-6"
        />
        <span
          className="text-sm font-semibold"
          style={{ color: getStatusTextColor(task.status) }}
        >
          {getStatusText(task.status)}
        </span>
      </div>

      {/* Файлы */}
      <div className="flex items-center justify-center text-sm text-white/80">
        {task.processed_files} / {task.total_files} файлов
      </div>

      {/* Дефекты */}
      <div className="flex items-center justify-center">
        <span
          className={`px-3 py-1 text-xs font-semibold rounded-full ${
            hasDefects ? "bg-red-500/30 text-red-200" : "bg-emerald-500/30 text-emerald-100"
          }`}
        >
          {hasDefects ? `${task.defects_found} дефектов` : "Без дефектов"}
        </span>
      </div>

      {/* Меню (три точки) */}
      <div className="relative flex items-center justify-end" onClick={(e) => e.stopPropagation()}>
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
              onClick={handleOpenTask}
              disabled={isProcessing}
              className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                isProcessing
                  ? "text-white/40 cursor-not-allowed"
                  : "text-white hover:bg-white/10"
              }`}
            >
              {isProcessing ? "Задача в обработке..." : "Открыть задачу"}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteTask();
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition-colors"
            >
              Удалить задачу
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

type SortType = "created_at" | "status" | "total_files" | "defects_found" | null;
type SortDirection = "asc" | "desc";

export default function TaskHistoryContents({ tasks, onTaskDeleted }: TaskHistoryContentsProps) {
  const [sortType, setSortType] = useState<SortType>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [isFilterMenuOpen, setIsFilterMenuOpen] = useState(false);
  const filterMenuRef = useRef<HTMLDivElement>(null);
  const filterButtonRef = useRef<HTMLButtonElement>(null);
  const [filterMenuPosition, setFilterMenuPosition] = useState({ top: 0, left: 0 });
  const navigate = useNavigate();

  const formatDate = useCallback((dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
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
  const sortedTasks = useMemo(() => {
    if (!sortType) return tasks || [];

    const sorted = [...(tasks || [])].sort((a, b) => {
      let comparison = 0;

      switch (sortType) {
        case "created_at":
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case "status":
          comparison = a.status.localeCompare(b.status, "ru");
          break;
        case "total_files":
          comparison = a.total_files - b.total_files;
          break;
        case "defects_found":
          comparison = a.defects_found - b.defects_found;
          break;
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });

    return sorted;
  }, [tasks, sortType, sortDirection]);

  const handleSortChange = useCallback((type: SortType) => {
    if (sortType === type) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortType(type);
      setSortDirection("asc");
    }
    // Меню не закрывается после выбора
  }, [sortType, sortDirection]);

  const handleOpenTask = useCallback((taskId: string) => {
    navigate(`/analysis?task_id=${taskId}`);
  }, [navigate]);

  // Удаление задачи
  const handleDeleteTask = useCallback(async (taskId: string) => {
    try {
      const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
      const response = await fetch(
        `${BFF_SERVICE_URL}/analysis/tasks/${taskId}`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete task');
      }

      // Если задача была удалена успешно, вызываем callback с taskId
      if (onTaskDeleted) {
        onTaskDeleted(taskId);
      }
    } catch (error) {
      console.error('Error deleting task:', error);
      alert('Не удалось удалить задачу');
    }
  }, [onTaskDeleted]);

  return (
    <motion.div
      key="task-history"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="w-full h-full flex flex-col gap-6"
    >
      <div className="space-y-8 flex-1 flex flex-col">
        {/* История задач */}
        <div className="relative flex-1 border border-white/20 rounded-xl flex flex-col bg-white/5">
          <div className="p-4 flex flex-wrap gap-4 items-center justify-between">
            <div>
              <p className="font-bold text-lg">История анализов</p>
              <p className="text-white/60 text-sm">{tasks.length} задач</p>
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
                      onClick={() => handleSortChange("created_at")}
                      className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                        sortType === "created_at"
                          ? "text-white bg-white/10"
                          : "text-white hover:bg-white/10"
                      }`}
                    >
                      <span>Дата создания</span>
                      {sortType === "created_at" && (
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
                    <button
                      onClick={() => handleSortChange("total_files")}
                      className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                        sortType === "total_files"
                          ? "text-white bg-white/10"
                          : "text-white hover:bg-white/10"
                      }`}
                    >
                      <span>Количество файлов</span>
                      {sortType === "total_files" && (
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
                      onClick={() => handleSortChange("defects_found")}
                      className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between ${
                        sortType === "defects_found"
                          ? "text-white bg-white/10"
                          : "text-white hover:bg-white/10"
                      }`}
                    >
                      <span>Дефекты</span>
                      {sortType === "defects_found" && (
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
            </div>
          </div>
          <hr className="border-white/10" />
          <div className="flex-1 overflow-hidden flex flex-col">
            {/* Заголовки колонок */}
            {sortedTasks.length > 0 && (
              <div
                className="pt-4 pb-2 grid grid-cols-[minmax(0,300px)_1fr_1fr_1fr_auto] items-center gap-8"
                style={{ paddingLeft: '32px', paddingRight: '32px' }}
              >
                <div className="flex items-center gap-4 min-w-0 max-w-[300px]">
                  <div className="w-14 flex-shrink-0"></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white/80">Название / Дата</p>
                  </div>
                </div>
                <div className="flex items-center justify-center">
                  <p className="text-sm font-semibold text-white/80">Статус</p>
                </div>
                <div className="flex items-center justify-center">
                  <p className="text-sm font-semibold text-white/80">Файлы</p>
                </div>
                <div className="flex items-center justify-center">
                  <p className="text-sm font-semibold text-white/80">Дефекты</p>
                </div>
                <div className="flex items-center justify-end w-10"></div>
              </div>
            )}
            <div className="h-full overflow-y-auto p-4 space-y-3">
              {sortedTasks.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-white/60 text-center gap-2">
                  <p className="text-lg font-semibold">История пока пуста</p>
                  <p className="text-sm text-white/50 max-w-sm">
                    Здесь будут отображаться все ваши задачи анализа изображений.
                  </p>
                </div>
              ) : (
                sortedTasks.map((task: TaskItemData) => (
                  <TaskItem
                    key={task.id}
                    task={task}
                    formatDate={formatDate}
                    onOpenTask={handleOpenTask}
                    onDeleteTask={handleDeleteTask}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

