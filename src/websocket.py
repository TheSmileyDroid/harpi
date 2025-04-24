"""WebSocket management module for handling
connections and broadcasting messages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Dict

from src.models.canvas import CanvasData, CanvasStorage

if TYPE_CHECKING:
    from fastapi import WebSocket

import logging
import time

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections
    and allows broadcasting messages to all active
    connections."""

    def __init__(self) -> None:
        """Initializes the WebSocketManager
        with an empty list of active connections."""
        self.active_connections: list[WebSocket] = []
        self.user_rooms: Dict[WebSocket, str] = {}
        self.canvas_storage = CanvasStorage()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.user_rooms:
            del self.user_rooms[websocket]

    async def broadcast(self, message: dict) -> None:
        for connection in self.active_connections:
            await connection.send_json(message)

    async def broadcast_to_room(self, room: str, message: dict) -> None:
        """Broadcast a message to all connections in a specific room."""
        for connection, user_room in self.user_rooms.items():
            if user_room == room and connection in self.active_connections:
                await connection.send_json(message)

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        """Process incoming WebSocket messages.

        Args:
            websocket (WebSocket): The client WebSocket connection
            message (str): The message received from the client
        """
        try:
            data = json.loads(message)
            message_type = data.get("type", "")

            # Processar mensagens relacionadas ao canvas
            if message_type == "join-canvas" and "guildId" in data:
                guild_id = str(data["guildId"])
                room_id = f"guild-{guild_id}"
                self.user_rooms[websocket] = room_id

            elif message_type == "get-canvas" and "guildId" in data:
                guild_id = str(data["guildId"])
                canvas_data = self.canvas_storage.get_canvas(guild_id)
                await websocket.send_json({
                    "entity": ["canvas"],
                    "type": "canvas-update",
                    "guildId": guild_id,
                    "canvasData": canvas_data.model_dump(),
                    "files": json.dumps(self.canvas_storage.get_files()),
                    "timestamp": 0,  # Timestamp zero para garantir que os dados sejam aplicados
                })

            elif message_type == "canvas-update" and "guildId" in data:
                guild_id = str(data["guildId"])
                room_id = f"guild-{guild_id}"

                self.canvas_storage.update_canvas(
                    guild_id,
                    CanvasData(**data["canvasData"]),
                    json.loads(data.get("files", "{}")),
                )

                logger.debug(
                    "CanvasData %s", str(CanvasData(**data["canvasData"]))
                )

                # Reenviar a atualização para todos os clientes da mesma sala
                # exceto o remetente
                for connection, user_room in self.user_rooms.items():
                    if (
                        user_room == room_id
                        and connection != websocket
                        and connection in self.active_connections
                    ):
                        logger.info(
                            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Enviando atualização de canvas para {connection.client}"
                        )
                        try:
                            await connection.send_json(data)
                        except Exception as e:
                            logger.error(
                                f"Erro ao enviar mensagem para {connection.client}: {e}"
                            )
                            self.disconnect(connection)

        except Exception as e:
            print(f"Erro ao processar mensagem WebSocket: {e}")


# Create global instance
manager = WebSocketManager()
