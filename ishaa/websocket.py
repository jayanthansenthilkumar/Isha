"""
Ishaa WebSocket Support — Real-time bidirectional communication.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("ishaa.websocket")


class WebSocket:
    """
    Represents a WebSocket connection.
    
    Example:
        @app.websocket("/ws")
        async def ws_handler(ws):
            await ws.accept()
            while True:
                data = await ws.receive_text()
                await ws.send_text(f"Echo: {data}")
    """

    def __init__(self, scope, receive, send):
        self.scope = scope
        self._receive = receive
        self._send = send
        self.path = scope.get("path", "/")
        self.headers = {}
        self.query_params = {}
        self.client = scope.get("client", ("127.0.0.1", 0))
        self._accepted = False
        self._closed = False

        # Parse headers
        for key, value in scope.get("headers", []):
            name = key.decode("latin-1") if isinstance(key, bytes) else key
            val = value.decode("latin-1") if isinstance(value, bytes) else value
            self.headers[name.lower()] = val

        # Parse query string
        from urllib.parse import parse_qs
        qs = scope.get("query_string", b"")
        if isinstance(qs, bytes):
            qs = qs.decode("utf-8")
        self.query_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(qs).items()}

    async def accept(self, subprotocol=None):
        """Accept the WebSocket connection."""
        msg = {"type": "websocket.accept"}
        if subprotocol:
            msg["subprotocol"] = subprotocol
        await self._send(msg)
        self._accepted = True

    async def close(self, code=1000, reason=""):
        """Close the WebSocket connection."""
        if not self._closed:
            await self._send({
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            })
            self._closed = True

    async def receive(self):
        """Receive a raw WebSocket message."""
        message = await self._receive()
        if message["type"] == "websocket.disconnect":
            self._closed = True
            raise WebSocketDisconnect(message.get("code", 1000))
        return message

    async def receive_text(self) -> str:
        """Receive a text message."""
        message = await self.receive()
        return message.get("text", "")

    async def receive_json(self) -> Any:
        """Receive a JSON message."""
        text = await self.receive_text()
        return json.loads(text) if text else None

    async def receive_bytes(self) -> bytes:
        """Receive a bytes message."""
        message = await self.receive()
        return message.get("bytes", b"")

    async def send_text(self, data: str):
        """Send a text message."""
        await self._send({"type": "websocket.send", "text": data})

    async def send_json(self, data: Any):
        """Send a JSON message."""
        await self.send_text(json.dumps(data, default=str))

    async def send_bytes(self, data: bytes):
        """Send a bytes message."""
        await self._send({"type": "websocket.send", "bytes": data})


class WebSocketDisconnect(Exception):
    """Raised when a WebSocket client disconnects."""

    def __init__(self, code=1000):
        self.code = code
        super().__init__(f"WebSocket disconnected with code {code}")


class WebSocketHandler:
    """Handles WebSocket connections for the Ishaa app."""

    def __init__(self, app, scope, receive, send):
        self.app = app
        self.scope = scope
        self.receive = receive
        self.send = send

    async def handle(self):
        """Route WebSocket connections to registered handlers."""
        path = self.scope.get("path", "/")
        ws = WebSocket(self.scope, self.receive, self.send)

        # Look up WebSocket route
        handler = self.app._state.get("_ws_routes", {}).get(path)
        if handler:
            try:
                await handler(ws)
            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await ws.close(1011, "Internal Error")
                except Exception:
                    pass
        else:
            await self.send({"type": "websocket.close", "code": 4004})


class WebSocketRoom:
    """
    Manages a group of WebSocket connections (like a chat room).
    
    Example:
        room = WebSocketRoom("chat")
        
        @app.websocket("/ws/chat")
        async def chat(ws):
            await ws.accept()
            room.add(ws)
            try:
                while True:
                    msg = await ws.receive_text()
                    await room.broadcast(f"User: {msg}")
            except WebSocketDisconnect:
                room.remove(ws)
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._connections: Set[WebSocket] = set()

    def add(self, ws: WebSocket):
        """Add a connection to the room."""
        self._connections.add(ws)

    def remove(self, ws: WebSocket):
        """Remove a connection from the room."""
        self._connections.discard(ws)

    @property
    def count(self):
        return len(self._connections)

    async def broadcast(self, message: str, exclude: WebSocket = None):
        """Send a message to all connections in the room."""
        disconnected = []
        for ws in self._connections:
            if ws is exclude:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self._connections.discard(ws)

    async def broadcast_json(self, data: Any, exclude: WebSocket = None):
        """Broadcast a JSON message."""
        await self.broadcast(json.dumps(data, default=str), exclude)

    async def close_all(self, code=1000, reason=""):
        """Close all connections in the room."""
        for ws in list(self._connections):
            try:
                await ws.close(code, reason)
            except Exception:
                pass
        self._connections.clear()


def websocket_route(app, path: str):
    """
    Decorator to register a WebSocket route on the app.
    
    Example:
        @websocket_route(app, "/ws")
        async def handler(ws):
            await ws.accept()
            ...
    """
    def decorator(func: Callable):
        if "_ws_routes" not in app._state:
            app._state["_ws_routes"] = {}
        app._state["_ws_routes"][path] = func
        return func
    return decorator
