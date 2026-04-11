"""
Assessment chat endpoints.

POST /api/v1/assessment/{application_id}/start  — create session, return session_id + opening message
WS   /ws/assessment/{session_id}                 — stream chat turns
POST /api/v1/assessment/{session_id}/finalize    — return structured JSON result
"""

import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from agents.assessment.agent import AssessmentSession

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store (sufficient for single-instance dev; use Redis for HA)
_sessions: dict[str, AssessmentSession] = {}


class StartRequest(BaseModel):
    applicant_data: dict


@router.post("/{application_id}/start")
async def start_assessment(application_id: str, req: StartRequest):
    session_id = str(uuid.uuid4())
    session = AssessmentSession(
        session_id=session_id,
        application_id=application_id,
        applicant_data=req.applicant_data,
    )
    opening = await session.start()
    _sessions[session_id] = session
    logger.info("Assessment session %s started for %s", session_id, application_id)
    return {"session_id": session_id, "opening": opening}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Return metadata for a pre-created session (session_id, opening, application_id)."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return {
        "session_id": session.session_id,
        "application_id": session.application_id,
        "opening": session.opening,
    }


@router.websocket("/ws/{session_id}")
async def assessment_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = _sessions.get(session_id)
    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            user_msg = data.get("message", "").strip()
            if not user_msg:
                continue

            reply, is_complete = await session.chat(user_msg)

            await websocket.send_json({
                "role": "assistant",
                "message": reply,
                "is_complete": is_complete,
            })

            if is_complete:
                break

    except WebSocketDisconnect:
        logger.info("Assessment WS disconnected: %s", session_id)
    except Exception as e:
        logger.error("Assessment WS error %s: %s", session_id, e)
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


@router.post("/{session_id}/finalize")
async def finalize_assessment(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = session.get_result()
    if not result:
        raise HTTPException(status_code=400, detail="Assessment not yet complete")

    # Clean up session
    _sessions.pop(session_id, None)
    return result
