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

AGENT_ROLE = "critic"  # Reviews and validates identity documents

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "identity_verification.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        pan_number=state.get("pan_number", ""),
        date_of_birth=state.get("date_of_birth", ""),
        verified_income=state.get("verified_income", 0),
    )


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_identity_verification(state: ApplicationState) -> ApplicationState:
    """
    Node 3: identity_verification
    Simulates PAN KYC: verifies PAN format, name match, and liveness check.
    Outputs: identity_verified, pan_verified, name_match, kyc_status.
    A failed KYC (kyc_status == 'failed' or 'mismatch') routes to rejection.
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
            "current_stage": "identity_verification",
            "identity_verified": bool(result.get("identity_verified", False)),
            "pan_verified": bool(result.get("pan_verified", False)),
            "name_match": bool(result.get("name_match", False)),
            "kyc_status": result.get("kyc_status", "failed"),
            "stage_results": {
                **state.get("stage_results", {}),
                "identity_verification": {
                    "identity_verified": result.get("identity_verified"),
                    "pan_verified": result.get("pan_verified"),
                    "name_match": result.get("name_match"),
                    "kyc_status": result.get("kyc_status"),
                    "pan_entity_type": result.get("pan_entity_type"),
                    "face_match_confidence": result.get("face_match_confidence"),
                    "kyc_notes": result.get("kyc_notes"),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "identity_verification",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("identity_verification failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "identity_verification",
            "identity_verified": False,
            "kyc_status": "failed",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"identity_verification: {e}"],
        }
