"""
Assessment proxy — routes all assessment traffic through backend-api so the
frontend only needs to reach one service. Eliminates the direct nginx →
agent-service path that breaks on Railway (separate private networks).

HTTP:  POST /api/v1/assessment/{id}/start
       GET  /api/v1/assessment/session/{sid}
       POST /api/v1/assessment/{sid}/finalize

WS:    /ws/assessment/{sid}  →  relayed to agent-service WS
"""

import asyncio
import logging

import httpx
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _agent_http_url(path: str) -> str:
    return f"{settings.agent_service_url}/api/v1/assessment{path}"


def _agent_ws_url(session_id: str) -> str:
    base = settings.agent_service_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/api/v1/assessment/ws/{session_id}"


# ── HTTP endpoints ─────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    applicant_data: dict


@router.post("/{application_id}/start")
async def proxy_start(application_id: str, req: StartRequest):
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                _agent_http_url(f"/{application_id}/start"),
                json=req.model_dump(),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Agent service unreachable: {e}")


@router.get("/session/{session_id}")
async def proxy_get_session(session_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(_agent_http_url(f"/session/{session_id}"))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Agent service unreachable: {e}")


@router.post("/{session_id}/finalize")
async def proxy_finalize(session_id: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(_agent_http_url(f"/{session_id}/finalize"))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Agent service unreachable: {e}")


# ── WebSocket relay ────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def proxy_assessment_ws(client_ws: WebSocket, session_id: str):
    """Bidirectional WS relay: browser ↔ backend-api ↔ agent-service."""
    await client_ws.accept()
    agent_url = _agent_ws_url(session_id)

    try:
        async with websockets.connect(agent_url) as agent_ws:

            async def client_to_agent():
                try:
                    async for msg in client_ws.iter_text():
                        await agent_ws.send(msg)
                except WebSocketDisconnect:
                    pass

            async def agent_to_client():
                try:
                    async for msg in agent_ws:
                        await client_ws.send_text(msg)
                except Exception:
                    pass

            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(client_to_agent()),
                    asyncio.create_task(agent_to_client()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except Exception as e:
        logger.error("Assessment WS relay error for %s: %s", session_id, e)
        try:
            await client_ws.send_json({"error": "Assessment service unavailable"})
        except Exception:
            pass
