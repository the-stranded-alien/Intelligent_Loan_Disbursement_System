import json
import logging
import re
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "lead_capture.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        phone=state.get("phone", ""),
        email=state.get("email", ""),
        pan_number=state.get("pan_number", ""),
        loan_amount=state.get("loan_amount", 0),
        loan_purpose=state.get("loan_purpose", ""),
        tenure_months=state.get("tenure_months", 12),
    )


def _parse_response(text: str) -> dict:
    """Extract JSON from Claude's response."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_lead_capture(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_capture
    Calls Claude to validate/normalize lead data and compute an initial lead score.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        result = _parse_response(raw)

        updated_state = {
            **state,
            "current_stage": "lead_capture",
            "lead_score": float(result.get("lead_score", 50)),
            "lead_source": result.get("lead_source", "web"),
            "phone": result.get("normalized_phone", state.get("phone", "")),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_capture": result,
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "lead_capture",
                "stage_results": updated_state.get("stage_results", {}),
            },
        )
        return updated_state
    except Exception as e:
        logger.error("lead_capture failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "lead_capture",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"lead_capture: {e}"],
        }
