import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from config.settings import settings
from db.session import SessionLocal
from db.models import Application, AuditLog
from services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class EventConsumer:
    STREAM = "loan:events"
    GROUP = "backend-api-group"
    CONSUMER = "backend-api-1"

    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._running = False

    async def connect(self):
        self._client = aioredis.from_url(settings.redis_streams_url, decode_responses=True)
        try:
            await self._client.xgroup_create(self.STREAM, self.GROUP, id="0", mkstream=True)
        except Exception:
            pass

    async def consume(self):
        self._running = True
        logger.info("Backend event consumer started")
        while self._running:
            try:
                results = await self._client.xreadgroup(
                    groupname=self.GROUP,
                    consumername=self.CONSUMER,
                    streams={self.STREAM: ">"},
                    count=10,
                    block=2000,
                )
                if not results:
                    continue
                for _stream, messages in results:
                    for msg_id, fields in messages:
                        await self._handle(msg_id, fields)
            except Exception as e:
                logger.error("Backend consumer error: %s", e)
                await asyncio.sleep(2)

    async def _handle(self, msg_id: str, fields: dict):
        event_type = fields.get("event_type")
        try:
            payload = json.loads(fields.get("payload", "{}"))
        except Exception:
            payload = {}

        if event_type == "node.started":
            application_id = payload.get("application_id")
            stage = payload.get("stage")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    app.current_stage = stage
                    app.status = "processing"
                    app.updated_at = datetime.now(timezone.utc)
                    db.commit()
            finally:
                db.close()
            await websocket_manager.broadcast(application_id, {
                "event": "node.started",
                "stage": stage,
            })

        elif event_type == "node.completed":
            application_id = payload.get("application_id")
            stage = payload.get("stage")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    app.current_stage = stage
                    app.updated_at = datetime.now(timezone.utc)
                    stage_result = payload.get("stage_results", {}).get(stage, {})
                    db.add(AuditLog(
                        id=str(uuid.uuid4()),
                        application_id=application_id,
                        event_type=f"stage.{stage}.completed",
                        actor="agent-service",
                        payload={"stage": stage, "result": stage_result},
                        created_at=datetime.now(timezone.utc),
                    ))
                    db.commit()
            finally:
                db.close()

            await websocket_manager.broadcast(application_id, {
                "event": "node.completed",
                "stage": stage,
                "data": payload,
            })

            # Node 2: if qualification is "request_info", mark app as info_requested
            # and auto-start an AssessmentSession so the applicant can chat immediately.
            if stage == "lead_qualification":
                stage_result = payload.get("stage_results", {}).get("lead_qualification", {})
                if stage_result.get("qualification_result") == "request_info":
                    db3 = SessionLocal()
                    applicant_data: dict = {}
                    try:
                        app3 = db3.query(Application).filter(Application.id == application_id).first()
                        if app3:
                            app3.status = "info_requested"
                            app3.updated_at = datetime.now(timezone.utc)
                            db3.commit()
                            applicant_data = {
                                "full_name": app3.full_name or "",
                                "monthly_income": float(app3.monthly_income or 0),
                                "existing_emi_amount": float(app3.existing_emi_amount or 0),
                                "loan_amount": float(app3.loan_amount or 0),
                                "tenure_months": int(app3.tenure_months or 12),
                                "employment_type": app3.employment_type or "salaried",
                                "loan_purpose": app3.loan_purpose or "",
                            }
                    finally:
                        db3.close()

                    # Broadcast basic info_requested event first
                    await websocket_manager.broadcast(application_id, {
                        "event": "info_requested",
                        "stage": "lead_qualification",
                        "reason": stage_result.get("qualification_notes", ""),
                    })

                    # Auto-create assessment session — fire-and-forget
                    if applicant_data:
                        asyncio.create_task(_start_assessment_session(
                            application_id=application_id,
                            applicant_data=applicant_data,
                        ))

            # Eligibility email: fire-and-forget when lead_capture passes
            if stage == "lead_capture":
                stage_result = payload.get("stage_results", {}).get("lead_capture", {})
                if stage_result.get("eligibility_result") == "eligible":
                    db2 = SessionLocal()
                    try:
                        app2 = db2.query(Application).filter(Application.id == application_id).first()
                        if app2 and app2.email:
                            asyncio.create_task(_send_eligibility_email(
                                application_id=application_id,
                                email=app2.email,
                                full_name=app2.full_name or "",
                                loan_amount=float(app2.loan_amount or 0),
                            ))
                    finally:
                        db2.close()

        elif event_type == "hitl.requested":
            application_id = payload.get("application_id")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    app.status = "pending_review"
                    app.updated_at = datetime.now(timezone.utc)
                    db.commit()
            finally:
                db.close()

            await websocket_manager.broadcast(application_id, {
                "event": "hitl.requested",
                "stage": "art_negotiation",
                "data": payload,
            })

        elif event_type == "pipeline.completed":
            application_id = payload.get("application_id")
            stage = payload.get("stage")
            final_status = payload.get("final_status", "completed")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    app.status = final_status
                    app.current_stage = stage
                    app.updated_at = datetime.now(timezone.utc)
                    db.commit()
            finally:
                db.close()

            await websocket_manager.broadcast(application_id, {
                "event": "pipeline.completed",
                "stage": stage,
                "status": final_status,
                "data": payload,
            })

        elif event_type == "outreach.required":
            application_id = payload.get("application_id")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    db.add(AuditLog(
                        id=str(uuid.uuid4()),
                        application_id=application_id,
                        event_type="outreach.triggered",
                        actor="monitoring-agent",
                        payload={
                            "hours_stale": payload.get("hours_stale"),
                            "status": payload.get("status"),
                            "current_stage": payload.get("current_stage"),
                            "outreach_attempt": payload.get("outreach_attempt"),
                        },
                        created_at=datetime.now(timezone.utc),
                    ))
                    db.commit()
            finally:
                db.close()

            await websocket_manager.broadcast(application_id, {
                "event": "outreach.required",
                "stage": payload.get("current_stage"),
                "hours_stale": payload.get("hours_stale"),
            })

        elif event_type == "outreach.sent":
            application_id = payload.get("application_id")
            await websocket_manager.broadcast(application_id, {
                "event": "outreach.sent",
                "attempt": payload.get("attempt"),
                "urgency": payload.get("urgency"),
                "subject": payload.get("subject"),
            })

        await self._client.xack(self.STREAM, self.GROUP, msg_id)

    async def close(self):
        self._running = False
        if self._client:
            await self._client.aclose()


async def _start_assessment_session(application_id: str, applicant_data: dict):
    """Fire-and-forget: create an AssessmentSession locally and broadcast session_id."""
    try:
        import uuid
        from routers.assessment_proxy import AssessmentSession, _sessions
        session_id = str(uuid.uuid4())
        session = AssessmentSession(session_id, application_id, applicant_data)
        opening = await session.start()
        _sessions[session_id] = session
        await websocket_manager.broadcast(application_id, {
            "event": "assessment_ready",
            "session_id": session_id,
            "opening": opening,
        })
        logger.info("Auto-started assessment session %s for %s", session_id, application_id)
    except Exception as e:
        logger.warning("Failed to auto-start assessment for %s: %s", application_id, e)


async def _send_eligibility_email(application_id: str, email: str, full_name: str, loan_amount: float):
    """Fire-and-forget: enqueue eligibility email via notification-service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.notification_service_url}/internal/send-outreach",
                json={
                    "application_id": application_id,
                    "email": email,
                    "phone": "",
                    "full_name": full_name,
                    "subject": "You're eligible — complete your KYC next",
                    "email_body": (
                        f"Hi {full_name.split()[0] if full_name else 'there'},\n\n"
                        f"Great news! Your loan application for ₹{int(loan_amount):,} has passed initial "
                        f"eligibility screening.\n\n"
                        f"Our AI pipeline is now verifying your identity (KYC). This usually takes just a "
                        f"few minutes — no action needed from you.\n\n"
                        f"We'll notify you as soon as each step is complete.\n\n"
                        f"LoanFlow Team"
                    ),
                    "sms_text": (
                        f"Hi {full_name.split()[0] if full_name else 'there'}! "
                        f"Your LoanFlow application is eligible. KYC in progress — no action needed."
                    ),
                },
            )
    except Exception as e:
        logger.warning("Failed to send eligibility email for %s: %s", application_id, e)
