import logging
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

AGENT_ROLE = "analyst"

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "credit_assessment.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        pan_number=state.get("pan_number", ""),
        employment_type=state.get("employment_type", "salaried"),
        verified_income=state.get("verified_income", state.get("monthly_income", 0)),
        existing_emi_amount=state.get("existing_emi_amount", 0),
        loan_amount=state.get("loan_amount", 0),
        tenure_months=state.get("tenure_months", 12),
        loan_purpose=state.get("loan_purpose", ""),
        max_eligible_amount=state.get("max_eligible_amount", state.get("loan_amount", 0)),
    )


def _publish_completed(application_id: str, stage_results: dict):
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": application_id,
            "stage": "credit_assessment",
            "stage_results": stage_results,
        },
    )


async def run_credit_assessment(state: ApplicationState) -> ApplicationState:
    """
    Node 4: credit_assessment
    Simulates CIBIL/Experian credit bureau pull.
    Outputs: credit_score (300-900), credit_decision (approve|reject), suggested_loan_amount.
    """
    application_id = state.get("application_id")

    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "credit_assessment"},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        result = parse_llm_json(response.content[0].text)

        # dti_ratio comes as 0–1 decimal; convert to percentage for UI
        raw_dti = result.get("dti_ratio", 0)
        dti_pct = round(float(raw_dti) * 100, 1) if raw_dti <= 1 else round(float(raw_dti), 1)

        stage_result = {
            "credit_score": result.get("credit_score"),
            "credit_decision": result.get("credit_decision"),
            "suggested_loan_amount": result.get("suggested_loan_amount"),
            "repayment_history": result.get("repayment_history"),
            "dti_ratio": dti_pct,
            "risk_grade": result.get("risk_grade"),
            "credit_notes": result.get("credit_notes"),
        }

        updated_state = {
            **state,
            "current_stage": "credit_assessment",
            "credit_score": int(result.get("credit_score", 600)),
            "credit_decision": result.get("credit_decision", "reject"),
            "suggested_loan_amount": float(result.get("suggested_loan_amount", 0)),
            "repayment_history": result.get("repayment_history", "fair"),
            "stage_results": {
                **state.get("stage_results", {}),
                "credit_assessment": stage_result,
            },
        }
        _publish_completed(application_id, updated_state["stage_results"])
        return updated_state

    except Exception as e:
        logger.error("credit_assessment failed for %s: %s", application_id, e)
        error_state = {
            **state,
            "current_stage": "credit_assessment",
            "credit_decision": "reject",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"credit_assessment: {e}"],
        }
        _publish_completed(application_id, error_state.get("stage_results", {}))
        return error_state
