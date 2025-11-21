import { useState, useEffect, useRef, useCallback } from "react";
import TaskHistoryContents from "./TaskHistoryContents";
import Loader from "./Loader";
import apiClient from "@/shared/api/axios";
import Breadcrumbs from "./Breadcrumbs";

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

interface TaskUpdateMessage {
  task_id: string;
  status: string;
  processed_files: number;
  total_files: number;
  failed_files: number;
  defects_found: number;
  message?: string;
}

export default function HistoryContent() {
  const [tasks, setTasks] = useState<TaskItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get("/analysis/history", {
        params: {
          limit: 100,
        },
      });

      setTasks(response.data);
    } catch (err: any) {
      console.error("Error loading tasks:", err);
      setError(
        err.response?.data?.detail || "Не удалось загрузить историю задач"
      );
    } finally {
      setLoading(false);
    }
  };

  // Обновление конкретной задачи в списке
  const updateTask = useCallback((update: TaskUpdateMessage) => {
    setTasks((prevTasks) => {
      const taskIndex = prevTasks.findIndex((t) => t.id === update.task_id);
      if (taskIndex === -1) {
        // Задача не найдена - возможно новая, перезагружаем список
        loadTasks();
        return prevTasks;
      }

      const newTasks = [...prevTasks];
      newTasks[taskIndex] = {
        ...newTasks[taskIndex],
        status: update.status,
        processed_files: update.processed_files,
        defects_found: update.defects_found,
        // Если задача завершена - обновляем completed_at
        completed_at:
          update.status.toLowerCase() === "completed" || update.status.toLowerCase() === "failed"
            ? new Date().toISOString()
            : newTasks[taskIndex].completed_at,
      };
      return newTasks;
    });
  }, []);

  // WebSocket подключение для реактивных обновлений
  useEffect(() => {
    const BFF_SERVICE_URL = (import.meta as any).env?.VITE_BFF_SERVICE_URL || "/api";
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}${BFF_SERVICE_URL}/ws/history`;

    const connectWebSocket = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected to history updates");
      };

      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data) as TaskUpdateMessage;
          console.log("Received task update:", update);
          updateTask(update);
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected, reconnecting in 3 seconds...");
        // Переподключаемся через 3 секунды
        setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [updateTask]);

  useEffect(() => {
    loadTasks();
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader />
          <p className="text-white/80 text-lg">Загрузка истории...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md">
          <h3 className="text-red-300 text-xl font-bold mb-2">Ошибка</h3>
          <p className="text-red-200">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" style={{ padding: '42px 96px 48px' }}>
      {/* Хлебные крошки */}
      <div className="mb-8">
        <Breadcrumbs
          items={[
            { label: "Главная", path: "/" },
            { label: "История" }
          ]}
        />
      </div>
      
      <div className="flex-1 flex flex-col">
        <TaskHistoryContents 
          tasks={tasks}
          onTaskDeleted={(taskId: string) => {
            // Удаляем задачу из локального состояния
            setTasks((prevTasks) => prevTasks.filter((task) => task.id !== taskId));
          }}
        />
      </div>
    </div>
  );
}

