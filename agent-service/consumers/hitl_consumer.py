import asyncio
import json
import logging

import redis.asyncio as aioredis

from config.settings import settings
from worker.tasks import resume_pipeline

logger = logging.getLogger(__name__)


class HitlDecisionConsumer:
    """Consumes RM HITL decisions from Redis Streams and enqueues resume_pipeline tasks."""

    STREAM = "loan:hitl:decisions"
    GROUP = "agent-hitl-group"
    CONSUMER = "agent-hitl-consumer"

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
        logger.info("HITL decision consumer started")
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
                logger.error("HITL consumer error: %s", e)
                await asyncio.sleep(2)

    async def _handle(self, msg_id: str, fields: dict):
        event_type = fields.get("event_type")
        try:
            payload = json.loads(fields.get("payload", "{}"))
        except Exception:
            payload = {}

        if event_type == "hitl.decision":
            application_id = payload.get("application_id")
            hitl_decision = {
                "decision": payload.get("decision"),
                "notes": payload.get("notes", ""),
                "rm_id": payload.get("rm_id", ""),
            }
            logger.info(
                "Enqueuing resume_pipeline for %s with decision=%s",
                application_id,
                hitl_decision["decision"],
            )
            resume_pipeline.delay(application_id, hitl_decision)

        await self._client.xack(self.STREAM, self.GROUP, msg_id)

    async def close(self):
        self._running = False
        if self._client:
            await self._client.aclose()
