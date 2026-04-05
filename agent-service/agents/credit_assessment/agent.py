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

AGENT_ROLE = "analyst"  # Quantitative credit risk analysis

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


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_credit_assessment(state: ApplicationState) -> ApplicationState:
    """
    Node 4: credit_assessment
    Simulates a CIBIL/Experian credit bureau pull using PAN + income data.
    Outputs: credit_score (300-900), credit_decision (approve|reject),
             suggested_loan_amount, repayment_history.
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
            "current_stage": "credit_assessment",
            "credit_score": int(result.get("credit_score", 600)),
            "credit_decision": result.get("credit_decision", "reject"),
            "suggested_loan_amount": float(result.get("suggested_loan_amount", 0)),
            "repayment_history": result.get("repayment_history", "fair"),
            "stage_results": {
                **state.get("stage_results", {}),
                "credit_assessment": {
                    "credit_score": result.get("credit_score"),
                    "credit_decision": result.get("credit_decision"),
                    "suggested_loan_amount": result.get("suggested_loan_amount"),
                    "repayment_history": result.get("repayment_history"),
                    "dti_ratio": result.get("dti_ratio"),
                    "risk_grade": result.get("risk_grade"),
                    "credit_notes": result.get("credit_notes"),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "credit_assessment",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("credit_assessment failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "credit_assessment",
            "credit_decision": "reject",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"credit_assessment: {e}"],
        }
