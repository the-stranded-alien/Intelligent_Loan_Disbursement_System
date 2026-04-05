import logging
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

AGENT_ROLE = "coordinator"

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "esign.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        application_id=state.get("application_id", ""),
        sanctioned_amount=state.get("sanctioned_amount", 0),
        interest_rate_percent=state.get("interest_rate_percent", 0),
        tenure_months=state.get("tenure_months", 12),
        monthly_emi=state.get("monthly_emi", 0),
        total_payable=state.get("total_payable", 0),
        processing_fee=state.get("processing_fee", 0),
        mandate_id=state.get("mandate_id", ""),
    )


async def run_esign(state: ApplicationState) -> ApplicationState:
    """
    Node 7: esign
    Simulates Aadhaar/OTP e-sign of the loan agreement. Terminal node.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        result = parse_llm_json(response.content[0].text)

        updated_state = {
            **state,
            "current_stage": "esign",
            "esign_status": result.get("esign_status", "failed"),
            "esign_reference": result.get("esign_reference"),
            "agreement_url": result.get("agreement_url"),
            "signed_at": result.get("signed_at"),
            "stage_results": {
                **state.get("stage_results", {}),
                "esign": {
                    "esign_status": result.get("esign_status"),
                    "esign_reference": result.get("esign_reference"),
                    "agreement_url": result.get("agreement_url"),
                    "signed_at": result.get("signed_at"),
                    "signature_method": result.get("signature_method"),
                    "esign_notes": result.get("esign_notes"),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "esign",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("esign failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "esign",
            "esign_status": "failed",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"esign: {e}"],
        }
