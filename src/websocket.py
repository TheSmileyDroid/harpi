"""WebSocket management module for handling
connections and broadcasting messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections
    and allows broadcasting messages to all active
    connections."""

    def __init__(self) -> None:
        """Initializes the WebSocketManager
        with an empty list of active connections."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in self.active_connections:
            await connection.send_json(message)


# Create global instance
manager = WebSocketManager()
