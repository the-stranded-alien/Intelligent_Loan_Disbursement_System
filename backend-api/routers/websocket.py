from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_manager import websocket_manager

router = APIRouter()


@router.websocket("/{application_id}")
async def pipeline_websocket(websocket: WebSocket, application_id: str):
    await websocket_manager.connect(application_id, websocket)
    try:
        await websocket.send_json({"event": "connected", "application_id": application_id})
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        websocket_manager.disconnect(application_id, websocket)
