"""
LLM call wrapper that captures token usage and latency metrics.

Usage:
    response, metrics = await call_llm(client, model=..., max_tokens=..., messages=...)
    # metrics = {"input_tokens": N, "output_tokens": N, "latency_ms": N}

The metrics dict is intended to be stored in stage_results so it flows
into the node.completed event and is persisted in the audit_log automatically.
"""

import time
import anthropic


async def call_llm(client: anthropic.AsyncAnthropic, **kwargs) -> tuple:
    """
    Call client.messages.create and return (response, metrics).
    metrics = {"input_tokens": int, "output_tokens": int, "latency_ms": int}
    """
    start = time.monotonic()
    response = await client.messages.create(**kwargs)
    latency_ms = round((time.monotonic() - start) * 1000)
    metrics = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }
    return response, metrics
