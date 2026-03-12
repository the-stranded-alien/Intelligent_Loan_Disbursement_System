from fastapi import WebSocket


class WebSocketManager:
    """Manages active WebSocket connections keyed by application_id."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, application_id: str, websocket: WebSocket):
        await websocket.accept()
        if application_id not in self.active_connections:
            self.active_connections[application_id] = []
        self.active_connections[application_id].append(websocket)

    def disconnect(self, application_id: str, websocket: WebSocket):
        if application_id in self.active_connections:
            self.active_connections[application_id].remove(websocket)
            if not self.active_connections[application_id]:
                del self.active_connections[application_id]

    async def broadcast(self, application_id: str, message: dict):
        if application_id in self.active_connections:
            dead = []
            for ws in self.active_connections[application_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(application_id, ws)


websocket_manager = WebSocketManager()
