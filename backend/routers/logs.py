import asyncio
import logging
import json
import time
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["Logs"])

# Global reference to the main event loop
MAIN_LOOP: Optional[asyncio.AbstractEventLoop] = None

def set_main_loop(loop: asyncio.AbstractEventLoop):
    global MAIN_LOOP
    MAIN_LOOP = loop

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._pending_broadcast: Optional[asyncio.Task] = None
        self._broadcast_buffer: List[str] = []
        self._last_emit_time: float = 0
        self._emit_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients with error handling"""
        if not self.active_connections:
            return

        # Use list copy to avoid modification during iteration issues
        disconnected = []
        for connection in list(self.active_connections):
            try:
                if connection.client_state.name != "DISCONNECTED":
                    await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def _flush_broadcast_buffer(self):
        """Flush buffered log messages in batch"""
        async with self._emit_lock:
            if not self._broadcast_buffer:
                return

            messages = self._broadcast_buffer.copy()
            self._broadcast_buffer.clear()

            # Send all messages as a single batch (newline separated)
            try:
                batch_message = "\n".join(messages)
                await self.broadcast(batch_message)
            except Exception as e:
                logging.getLogger().error(f"[WS_MANAGER] Broadcast error: {e}")

manager = WebSocketManager()

class WebSocketLogHandler(logging.Handler):
    """
    Custom logging handler with rate limiting to prevent WebSocket spam.
    Buffers log messages and broadcasts them in batches.
    """
    def __init__(self, manager: WebSocketManager):
        super().__init__()
        self.manager = manager
        self._min_emit_interval = 0.1  # 100ms minimum between broadcasts

    def emit(self, record: logging.LogRecord):
        try:
            # Rate limiting: skip if too frequent
            now = time.time()
            time_since_last = now - self.manager._last_emit_time

            log_entry = self.format(record)
            payload = json.dumps({
                "timestamp": record.created,
                "level": record.levelname,
                "name": record.name,
                "message": log_entry
            })

            # Buffer the message
            self.manager._broadcast_buffer.append(payload)

            # Schedule broadcast if enough time passed
            if time_since_last >= self._min_emit_interval:
                self.manager._last_emit_time = now
                self._schedule_broadcast()

        except Exception:
            self.handleError(record)

    def _schedule_broadcast(self):
        """Schedule broadcast on the main event loop"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self.manager._flush_broadcast_buffer())
        except RuntimeError:
            # No running event loop, use stored main loop
            if MAIN_LOOP and not MAIN_LOOP.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.manager._flush_broadcast_buffer(),
                    MAIN_LOOP
                )

@router.websocket("/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send a welcome message
        await websocket.send_text(json.dumps({
            "level": "INFO",
            "message": "Terminal bağlantısı kuruldu. Loglar bekleniyor...",
            "name": "system",
            "timestamp": 0
        }))
        
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket)

def get_log_handler():
    return WebSocketLogHandler(manager)
