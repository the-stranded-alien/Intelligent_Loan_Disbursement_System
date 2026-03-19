import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

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

        if event_type == "node.completed":
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
                "stage": "sanction_processing",
                "data": payload,
            })

        elif event_type == "pipeline.completed":
            application_id = payload.get("application_id")
            stage = payload.get("stage")
            db = SessionLocal()
            try:
                app = db.query(Application).filter(Application.id == application_id).first()
                if app:
                    app.status = "completed"
                    app.current_stage = stage
                    app.updated_at = datetime.now(timezone.utc)
                    db.commit()
            finally:
                db.close()

            await websocket_manager.broadcast(application_id, {
                "event": "pipeline.completed",
                "stage": stage,
                "data": payload,
            })

        await self._client.xack(self.STREAM, self.GROUP, msg_id)

    async def close(self):
        self._running = False
        if self._client:
            await self._client.aclose()
