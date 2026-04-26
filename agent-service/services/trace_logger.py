"""
Lightweight trace writer — logs one row to agent_traces per LLM call.
Called synchronously from async agent nodes; the DB write is fast enough
that run_in_executor is not needed for this use case.
"""

import logging
import uuid
from datetime import datetime, timezone

from db.session import SessionLocal, AgentTrace

logger = logging.getLogger(__name__)


def log_trace(
    *,
    application_id: str | None,
    agent_role: str,
    node_name: str,
    prompt: str,
    raw_response: str,
    parsed_output: dict,
    metrics: dict,
    model: str = "claude-sonnet-4-6",
) -> None:
    """Write a single AgentTrace row. Errors are logged but never bubble up."""
    trace_id = str(uuid.uuid4())
    try:
        db = SessionLocal()
        try:
            db.add(AgentTrace(
                id=trace_id,
                application_id=application_id,
                agent_role=agent_role,
                node_name=node_name,
                prompt_rendered=prompt,
                raw_llm_response=raw_response,
                parsed_output=parsed_output,
                duration_ms=int(metrics.get("latency_ms", 0)),
                model=model,
                input_tokens=metrics.get("input_tokens", 0),
                output_tokens=metrics.get("output_tokens", 0),
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()
            logger.info("trace_logger OK  node=%s app=%s trace=%s", node_name, application_id, trace_id)
        finally:
            db.close()
    except Exception as e:
        logger.error("trace_logger FAIL node=%s app=%s error=%r", node_name, application_id, e)
