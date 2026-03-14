import asyncio
import json
import logging
import redis.asyncio as aioredis
from config.settings import settings
from worker.tasks import run_pipeline

logger = logging.getLogger(__name__)

class AgentEventConsumer:
    """Consumes pipeline trigger events from Redis Streams and enqueues Celery tasks."""

    STREAM = "loan:applications"
    GROUP = "agent-service-group"
    CONSUMER = "agent-service-consumer"

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
        logger.info("Agent event consumer started")
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
                logger.error("Consumer error: %s", e)
                await asyncio.sleep(2)

    async def _handle(self, msg_id: str, fields: dict):
        event_type = fields.get("event_type")
        try:
            payload = json.loads(fields.get("payload", "{}"))
        except Exception:
            payload = {}

        if event_type == "application.created":
            application_id = payload.get("application_id")
            logger.info("Enqueuing run_pipeline for %s", application_id)
            run_pipeline.delay(application_id, payload)

        await self._client.xack(self.STREAM, self.GROUP, msg_id)

    async def close(self):
        self._running = False
        if self._client:
            await self._client.aclose()
