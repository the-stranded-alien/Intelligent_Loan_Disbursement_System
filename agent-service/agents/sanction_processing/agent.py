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

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "sanction_processing.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        loan_amount=state.get("loan_amount", 0),
        tenure_months=state.get("tenure_months", 12),
        loan_purpose=state.get("loan_purpose", ""),
        credit_score=state.get("credit_score"),
        credit_decision=state.get("credit_decision", "N/A"),
        suggested_loan_amount=state.get("suggested_loan_amount", state.get("loan_amount", 0)),
        fraud_risk_score=state.get("fraud_risk_score", 0.0),
        compliance_decision=state.get("compliance_decision", "N/A"),
        hitl_decision=state.get("hitl_decision"),
        hitl_notes=state.get("hitl_notes", ""),
    )


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_sanction_processing(state: ApplicationState) -> ApplicationState:
    """
    Node: sanction_processing
    Responsibility: Compute final sanctioned amount, terms, and interest rate via Claude.
    For loans > HITL_THRESHOLD (₹10L), the graph was interrupted before this node ran
    and the RM decision was injected into state before resuming — so hitl_decision will
    already be present when this node executes for large loans.
    """
    loan_amount = state.get("loan_amount", 0)
    hitl_required = loan_amount > settings.hitl_threshold

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        result = _parse_response(raw)

        updated_state = {
            **state,
            "current_stage": "sanction_processing",
            "hitl_required": hitl_required,
            "sanction_amount": float(result.get("sanction_amount", 0)),
            "sanction_terms": {
                "interest_rate_percent": result.get("interest_rate_percent"),
                "tenure_months": result.get("tenure_months"),
                "monthly_emi": result.get("monthly_emi"),
                "total_payable": result.get("total_payable"),
                "processing_fee": result.get("processing_fee"),
                "terms_and_conditions": result.get("terms_and_conditions", []),
            },
            "stage_results": {
                **state.get("stage_results", {}),
                "sanction_processing": result,
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "sanction_processing",
                "stage_results": updated_state.get("stage_results", {}),
            },
        )
        return updated_state

    except Exception as e:
        logger.error("sanction_processing failed for %s: %s", state.get("application_id"), e)
        updated_state = {
            **state,
            "current_stage": "sanction_processing",
            "hitl_required": hitl_required,
            "pipeline_errors": [*state.get("pipeline_errors", []), f"sanction_processing: {e}"],
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "sanction_processing",
                "stage_results": updated_state.get("stage_results", {}),
            },
        )
        return updated_state
