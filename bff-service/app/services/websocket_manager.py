from collections import defaultdict
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket


class TaskWebSocketManager:
    def __init__(self) -> None:
        self.connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)

    async def connect(self, task_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[task_id].add(websocket)

    def disconnect(self, task_id: UUID, websocket: WebSocket) -> None:
        if task_id in self.connections and websocket in self.connections[task_id]:
            self.connections[task_id].remove(websocket)
        if task_id in self.connections and not self.connections[task_id]:
            del self.connections[task_id]

    async def send_to_task(self, task_id: UUID, data: dict) -> None:
        import logging
        logger = logging.getLogger(__name__)
        connections = self.connections.get(task_id)
        if not connections:
            logger.warning(f"No WebSocket connections found for task_id: {task_id}")
            return

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

    async def broadcast(self, data: dict) -> None:
        for task_id in list(self.connections.keys()):
            await self.send_to_task(task_id, data)


task_ws_manager = TaskWebSocketManager()

