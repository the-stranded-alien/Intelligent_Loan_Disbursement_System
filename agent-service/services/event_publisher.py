import json
import redis
from config.settings import settings


class EventPublisher:
    """Publishes pipeline events to Redis Streams."""

    def __init__(self):
        self._client: redis.Redis | None = None

    def connect(self):
        self._client = redis.from_url(settings.redis_streams_url, decode_responses=True)

    def publish(self, stream: str, event_type: str, payload: dict) -> str:
        if not self._client:
            self.connect()
        try:
            msg_id = self._client.xadd(
                stream,
                {"event_type": event_type, "payload": json.dumps(payload)},
            )
            return msg_id
        except Exception:
            return None

    def close(self):
        if self._client:
            self._client.close()

event_publisher = EventPublisher()
