"""
LangSmith tracing setup.

LangGraph automatically emits traces when LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY are set. This module also provides a @traced decorator
for non-LangGraph LLM calls (outreach, assessment, negotiation agents).
"""

import functools
import logging
import os
from config.settings import settings

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """
    Push LangSmith settings into environment so the SDK picks them up.
    Call once at service startup (main.py lifespan).
    """
    if settings.langchain_tracing_v2.lower() == "true" and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        logger.info("LangSmith tracing enabled — project: %s", settings.langchain_project)
    else:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
        logger.debug("LangSmith tracing disabled")


def traced(name: str):
    """
    Decorator that wraps an async agent function in a LangSmith run span.
    No-op if tracing is disabled.
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            if os.environ.get("LANGCHAIN_TRACING_V2") != "true":
                return await fn(*args, **kwargs)
            try:
                from langsmith import traceable  # noqa: PLC0415
                return await traceable(fn, name=name)(*args, **kwargs)
            except Exception:
                # Tracing failure must never break the agent
                return await fn(*args, **kwargs)
        return wrapper
    return decorator
