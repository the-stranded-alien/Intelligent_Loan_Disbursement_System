from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/{application_id}")
async def pipeline_websocket(websocket: WebSocket, application_id: str):
    # TODO: Accept WS connection, stream real-time pipeline stage updates
    await websocket.accept()
    await websocket.send_json({"status": "connected", "application_id": application_id})
    await websocket.close()
