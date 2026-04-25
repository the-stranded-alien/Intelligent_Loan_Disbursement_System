import logging
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json
from services.llm_utils import call_llm
from services.trace_logger import log_trace

logger = logging.getLogger(__name__)

AGENT_ROLE = "critic"

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "identity_verification.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        pan_number=state.get("pan_number", ""),
        date_of_birth=state.get("date_of_birth", ""),
        verified_income=state.get("verified_income", 0),
    )


def _publish_completed(application_id: str, stage_results: dict):
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": application_id,
            "stage": "identity_verification",
            "stage_results": stage_results,
        },
    )


async def run_identity_verification(state: ApplicationState) -> ApplicationState:
    """
    Node 3: identity_verification
    Simulates PAN KYC: format check, name match, liveness check.
    Outputs: identity_verified, pan_verified, name_match, kyc_status.
    """
    application_id = state.get("application_id")

    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "identity_verification"},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response, metrics = await call_llm(
            client,
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        result = parse_llm_json(raw)
        log_trace(application_id=application_id, agent_role=AGENT_ROLE, node_name="identity_verification",
                  prompt=prompt, raw_response=raw, parsed_output=result, metrics=metrics)

        # face_match_confidence comes as 0.0–1.0; convert to percentage for UI
        raw_conf = result.get("face_match_confidence", 0)
        face_conf_pct = round(float(raw_conf) * 100, 1) if raw_conf <= 1 else round(float(raw_conf), 1)

        stage_result = {
            "identity_verified": result.get("identity_verified"),
            "pan_verified": result.get("pan_verified"),
            "name_match": result.get("name_match"),
            "kyc_status": result.get("kyc_status"),
            "pan_entity_type": result.get("pan_entity_type"),
            "face_match_confidence": face_conf_pct,
            "kyc_notes": result.get("kyc_notes"),
            **metrics,
        }

        updated_state = {
            **state,
            "current_stage": "identity_verification",
            "identity_verified": bool(result.get("identity_verified", False)),
            "pan_verified": bool(result.get("pan_verified", False)),
            "name_match": bool(result.get("name_match", False)),
            "kyc_status": result.get("kyc_status", "failed"),
            "stage_results": {
                **state.get("stage_results", {}),
                "identity_verification": stage_result,
            },
        }
        _publish_completed(application_id, updated_state["stage_results"])
        return updated_state

    except Exception as e:
        logger.error("identity_verification failed for %s: %s", application_id, e)
        error_state = {
            **state,
            "current_stage": "identity_verification",
            "identity_verified": False,
            "kyc_status": "failed",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"identity_verification: {e}"],
        }
        _publish_completed(application_id, error_state.get("stage_results", {}))
        return error_state
