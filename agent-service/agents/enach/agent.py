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

AGENT_ROLE = "coordinator"  # Orchestrates e-NACH mandate setup with NPCI

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "enach.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        sanctioned_amount=state.get("sanctioned_amount", 0),
        monthly_emi=state.get("monthly_emi", 0),
        tenure_months=state.get("tenure_months", 12),
        bank_account_number=state.get("bank_account_number", ""),
        ifsc_code=state.get("ifsc_code", ""),
    )


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_enach(state: ApplicationState) -> ApplicationState:
    """
    Node 6: enach
    Simulates e-NACH auto-debit mandate registration with NPCI for EMI collection.
    Outputs: enach_status (success|failed|pending), mandate_id, enach_reference.
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
            "current_stage": "enach",
            "enach_status": result.get("enach_status", "failed"),
            "mandate_id": result.get("mandate_id"),
            "enach_reference": result.get("enach_reference"),
            "stage_results": {
                **state.get("stage_results", {}),
                "enach": {
                    "enach_status": result.get("enach_status"),
                    "mandate_id": result.get("mandate_id"),
                    "enach_reference": result.get("enach_reference"),
                    "bank_validated": result.get("bank_validated"),
                    "account_verified": result.get("account_verified"),
                    "mandate_amount": result.get("mandate_amount"),
                    "debit_date": result.get("debit_date"),
                    "enach_notes": result.get("enach_notes"),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "enach",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("enach failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "enach",
            "enach_status": "failed",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"enach: {e}"],
        }
