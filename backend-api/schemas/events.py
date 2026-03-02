from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class StreamEvent(BaseModel):
    event_type: str
    application_id: str
    payload: dict[str, Any]
    timestamp: datetime
    source_service: str


class PipelineEvent(StreamEvent):
    stage: str
    status: str
    result: Optional[dict[str, Any]] = None
