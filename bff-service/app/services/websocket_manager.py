from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket


class TaskWebSocketManager:
    def __init__(self) -> None:
        self.connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        self.history_connections: Set[WebSocket] = set()

    async def connect(self, task_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[task_id].add(websocket)

    def disconnect(self, task_id: UUID, websocket: WebSocket) -> None:
        if task_id in self.connections and websocket in self.connections[task_id]:
            self.connections[task_id].remove(websocket)
        if task_id in self.connections and not self.connections[task_id]:
            del self.connections[task_id]

    async def connect_history(self, websocket: WebSocket) -> None:
        """Подключить WebSocket для получения обновлений истории всех задач"""
        await websocket.accept()
        self.history_connections.add(websocket)

    def disconnect_history(self, websocket: WebSocket) -> None:
        """Отключить WebSocket от получения обновлений истории"""
        if websocket in self.history_connections:
            self.history_connections.remove(websocket)

    async def send_to_task(self, task_id: UUID, data: dict) -> None:
        import logging
        logger = logging.getLogger(__name__)
        
        # Отправляем подключениям конкретной задачи
        connections = self.connections.get(task_id)
        if connections:
            logger.info(f"Sending update to {len(connections)} connection(s) for task_id: {task_id}")
            disconnected = []
            for connection in connections:
                try:
                    await connection.send_json(data)
                    logger.info(f"Successfully sent update to WebSocket for task_id: {task_id}")
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}", exc_info=True)
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(task_id, conn)
        
        # Также отправляем всем подключениям истории
        await self.send_to_history(data)

    async def send_to_history(self, data: dict) -> None:
        """Отправить обновление всем подписчикам истории"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.history_connections:
            return
        
        logger.info(f"Sending update to {len(self.history_connections)} history connection(s)")
        disconnected = []
        for connection in self.history_connections:
            try:
                await connection.send_json(data)
                logger.info(f"Successfully sent update to history WebSocket")
            except Exception as e:
                logger.error(f"Error sending to history WebSocket: {e}", exc_info=True)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect_history(conn)

    async def broadcast(self, data: dict) -> None:
        for task_id in list(self.connections.keys()):
            await self.send_to_task(task_id, data)


task_ws_manager = TaskWebSocketManager()

