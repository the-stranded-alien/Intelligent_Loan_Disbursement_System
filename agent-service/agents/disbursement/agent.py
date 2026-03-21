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
_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "disbursement.j2"

def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        sanction_amount=state.get("sanction_amount", ""),
        account_number=state.get("account_number", "N/A"),
        ifsc_code=state.get("ifsc_code", "N/A"),
        disbursement_attempts=state.get("disbursement_attempts", 0)
    )

def _parse_response(text: str) -> dict:
    """Extract JSON from Claude's response."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)

async def run_disbursement(state: ApplicationState) -> ApplicationState:
    """
    Node: disbursement
    Responsibility: Initiate bank transfer via payment rail, confirm transaction,
    publish disbursement event. Retry schedule: immediate → 1h → 4h → 24h.
    """
    # TODO: Call disbursement tool, handle success/failure,
    #       set disbursement_status, disbursement_reference

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
            "current_stage": "disbursement",
            "disbursement_status": "pending",
            "disbursement_attempts": state.get("disbursement_attempts", 0) + 1,
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "disbursement",
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
