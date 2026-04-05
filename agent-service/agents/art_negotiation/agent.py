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

AGENT_ROLE = "planner"  # Synthesises all upstream outputs into final loan offer

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "art_negotiation.j2"


def _render_prompt(state: ApplicationState) -> str:
    verified_income = state.get("verified_income", state.get("monthly_income", 0))
    existing_emi = state.get("existing_emi_amount", 0)
    available_capacity = max(0, verified_income * 0.5 - existing_emi)

    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        employment_type=state.get("employment_type", "salaried"),
        verified_income=verified_income,
        existing_emi_amount=existing_emi,
        available_capacity=round(available_capacity, 2),
        loan_amount=state.get("loan_amount", 0),
        tenure_months=state.get("tenure_months", 12),
        loan_purpose=state.get("loan_purpose", ""),
        credit_score=state.get("credit_score", 650),
        risk_grade=state.get("stage_results", {}).get("credit_assessment", {}).get("risk_grade", "B"),
        credit_decision=state.get("credit_decision", "approve"),
        suggested_loan_amount=state.get("suggested_loan_amount", state.get("loan_amount", 0)),
        repayment_history=state.get("repayment_history", "fair"),
        max_eligible_amount=state.get("max_eligible_amount", state.get("loan_amount", 0)),
        hitl_decision=state.get("hitl_decision"),
        hitl_notes=state.get("hitl_notes", ""),
    )


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_art_negotiation(state: ApplicationState) -> ApplicationState:
    """
    Node 5: art_negotiation
    Planner node — synthesises credit score, income, and RM decision (if HITL)
    to produce 3 loan offer options (Amount, Rate, Tenure).
    For loans > HITL_THRESHOLD (₹2L), graph is interrupted before this node and
    resumed after RM approves/rejects.
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
            "current_stage": "art_negotiation",
            "hitl_required": hitl_required,
            "negotiation_offers": result.get("negotiation_offers", []),
            "selected_offer": next(
                (o for o in result.get("negotiation_offers", [])
                 if o.get("option") == result.get("selected_option", "B")),
                result.get("negotiation_offers", [{}])[0] if result.get("negotiation_offers") else {},
            ),
            "sanctioned_amount": float(result.get("sanctioned_amount", 0)),
            "interest_rate_percent": float(result.get("interest_rate_percent", 0)),
            "monthly_emi": float(result.get("monthly_emi", 0)),
            "total_payable": float(result.get("total_payable", 0)),
            "processing_fee": float(result.get("processing_fee", 0)),
            "stage_results": {
                **state.get("stage_results", {}),
                "art_negotiation": {
                    "sanctioned_amount": result.get("sanctioned_amount"),
                    "interest_rate_percent": result.get("interest_rate_percent"),
                    "monthly_emi": result.get("monthly_emi"),
                    "total_payable": result.get("total_payable"),
                    "processing_fee": result.get("processing_fee"),
                    "selected_option": result.get("selected_option"),
                    "offer_count": len(result.get("negotiation_offers", [])),
                    "planner_notes": result.get("planner_notes"),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "art_negotiation",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("art_negotiation failed for %s: %s", state.get("application_id"), e)
        updated_state = {
            **state,
            "current_stage": "art_negotiation",
            "hitl_required": hitl_required,
            "pipeline_errors": [*state.get("pipeline_errors", []), f"art_negotiation: {e}"],
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "art_negotiation",
                "stage_results": updated_state.get("stage_results", {}),
            },
        )
        return updated_state
