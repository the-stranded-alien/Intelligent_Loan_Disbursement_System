import logging
from pathlib import Path

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.llm_utils import call_llm

import anthropic

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "disbursement.j2"


def _render_prompt(state: ApplicationState) -> str:
    from jinja2 import Template
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        sanctioned_amount=state.get("sanctioned_amount", 0),
        bank_account_number=state.get("bank_account_number", "N/A"),
        ifsc_code=state.get("ifsc_code", "N/A"),
        disbursement_attempts=state.get("disbursement_attempts", 0),
        interest_rate_percent=state.get("interest_rate_percent", 0),
        monthly_emi=state.get("monthly_emi", 0),
    )


async def run_disbursement(state: ApplicationState) -> ApplicationState:
    """
    Node 8: disbursement
    Confirms loan terms with Claude, then deterministically marks disbursement as
    successful. In production replace the stub with a real IMPS/NEFT API call and
    raise on failure to trigger the Celery retry_disbursement task.
    """
    application_id = state.get("application_id")

    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "disbursement"},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response, metrics = await call_llm(
            client,
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        # Deterministic disbursement reference (no real bank API yet)
        disbursement_ref = f"DISB-{(application_id or 'UNKNOWN')[:8].upper()}-01"

        updated_state = {
            **state,
            "current_stage": "disbursement",
            "disbursement_status": "success",
            "disbursement_reference": disbursement_ref,
            "disbursement_attempts": state.get("disbursement_attempts", 0) + 1,
            "stage_results": {
                **state.get("stage_results", {}),
                "disbursement": {
                    "disbursement_status": "success",
                    "disbursement_reference": disbursement_ref,
                    "sanctioned_amount": state.get("sanctioned_amount"),
                    "bank_account_number": state.get("bank_account_number"),
                    **metrics,
                },
            },
        }

        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": application_id,
                "stage": "disbursement",
                "stage_results": updated_state["stage_results"],
            },
        )
        # Signal the full pipeline as disbursed
        event_publisher.publish(
            stream="loan:events",
            event_type="pipeline.completed",
            payload={
                "application_id": application_id,
                "stage": "disbursement",
                "final_status": "disbursed",
                "disbursement_ref": disbursement_ref,
            },
        )
        return updated_state

    except Exception as e:
        logger.error("disbursement failed for %s: %s", application_id, e)
        return {
            **state,
            "current_stage": "disbursement",
            "disbursement_status": "failed",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"disbursement: {e}"],
        }
