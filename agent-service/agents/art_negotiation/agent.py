import logging
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json
from services.llm_utils import call_llm

logger = logging.getLogger(__name__)

AGENT_ROLE = "planner"


def _emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI formula."""
    if tenure_months <= 0 or principal <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        return round(principal / tenure_months, 2)
    r = annual_rate_pct / 12 / 100
    return round(principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1), 2)


def _recompute_offer(offer: dict) -> dict:
    """Replace LLM-computed financials with exact Python calculations."""
    principal = float(offer.get("sanctioned_amount", 0))
    rate      = float(offer.get("interest_rate_percent", 10.5))
    tenure    = int(offer.get("tenure_months", 12))
    emi       = _emi(principal, rate, tenure)
    credit_score = offer.get("_credit_score", 700)
    fee_pct   = 0.02 if credit_score < 650 else 0.01
    return {
        **offer,
        "monthly_emi":    emi,
        "total_payable":  round(emi * tenure, 2),
        "total_interest": round(emi * tenure - principal, 2),
        "processing_fee": round(principal * fee_pct, 2),
    }

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


async def run_art_negotiation(state: ApplicationState) -> ApplicationState:
    """
    Node 5: art_negotiation
    Planner node — synthesises all upstream outputs into 3 loan offer options.
    HITL interrupt for loans > ₹2L.
    """
    application_id = state.get("application_id")
    loan_amount = state.get("loan_amount", 0)
    hitl_required = loan_amount > settings.hitl_threshold

    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "art_negotiation"},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state)

    try:
        response, metrics = await call_llm(
            client,
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result = parse_llm_json(response.content[0].text)

        # Recompute all financial fields in Python — LLM arithmetic is unreliable
        credit_score = state.get("credit_score") or 700
        raw_offers = result.get("negotiation_offers", [])
        offers = [
            _recompute_offer({**o, "_credit_score": credit_score})
            for o in raw_offers
        ]
        # Strip the internal helper key
        for o in offers:
            o.pop("_credit_score", None)

        selected_option = result.get("selected_option", "B")
        selected = next(
            (o for o in offers if o.get("option") == selected_option),
            offers[0] if offers else {},
        )

        updated_state = {
            **state,
            "current_stage": "art_negotiation",
            "hitl_required": hitl_required,
            "negotiation_offers": offers,
            "selected_offer": selected,
            "sanctioned_amount":    float(selected.get("sanctioned_amount", 0)),
            "interest_rate_percent": float(selected.get("interest_rate_percent", 0)),
            "monthly_emi":          float(selected.get("monthly_emi", 0)),
            "total_payable":        float(selected.get("total_payable", 0)),
            "processing_fee":       float(selected.get("processing_fee", 0)),
            "stage_results": {
                **state.get("stage_results", {}),
                "art_negotiation": {
                    "sanctioned_amount":    selected.get("sanctioned_amount"),
                    "interest_rate_percent": selected.get("interest_rate_percent"),
                    "monthly_emi":          selected.get("monthly_emi"),
                    "total_payable":        selected.get("total_payable"),
                    "processing_fee":       selected.get("processing_fee"),
                    "selected_option":      selected_option,
                    "offer_count":          len(offers),
                    "planner_notes":        result.get("planner_notes"),
                    "offers":               offers,
                    "recommended_option":   selected_option,
                    **metrics,
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
