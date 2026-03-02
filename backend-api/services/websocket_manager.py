from fastapi import WebSocket


class WebSocketManager:
    """Manages active WebSocket connections keyed by application_id."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, application_id: str, websocket: WebSocket):
        # TODO: Register websocket under application_id
        pass

    def disconnect(self, application_id: str, websocket: WebSocket):
        # TODO: Remove websocket from active connections
        pass

    async def broadcast(self, application_id: str, message: dict):
        # TODO: Send message to all connections for application_id
        pass


websocket_manager = WebSocketManager()
