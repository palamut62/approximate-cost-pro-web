import asyncio
import logging
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["Logs"])

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Using a list to avoid issues with modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                # Connection might be dead, disconnect it
                self.disconnect(connection)

manager = WebSocketManager()

class WebSocketLogHandler(logging.Handler):
    """
    Custom logging handler that broadcasts log records to all connected WebSocket clients.
    """
    def __init__(self, manager: WebSocketManager):
        super().__init__()
        self.manager = manager

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)
            payload = json.dumps({
                "timestamp": record.created,
                "level": record.levelname,
                "name": record.name,
                "message": log_entry
            })
            
            # Since emit is called from potentially anywhere (not always async),
            # we use the current running loop to schedule the broadcast.
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.manager.broadcast(payload))
            except RuntimeError:
                # No running event loop in this thread, try to find the main loop if possible
                # or skip it if we are in a non-async thread that shouldn't block
                pass
        except Exception:
            self.handleError(record)

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
