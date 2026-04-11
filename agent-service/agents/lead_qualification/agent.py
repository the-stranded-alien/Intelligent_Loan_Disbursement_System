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

AGENT_ROLE = "analyst"

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "lead_qualification.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        employment_type=state.get("employment_type", "salaried"),
        monthly_income=state.get("monthly_income", 0),
        existing_emi_amount=state.get("existing_emi_amount", 0),
        loan_amount=state.get("loan_amount", 0),
        tenure_months=state.get("tenure_months", 12),
        loan_purpose=state.get("loan_purpose", ""),
    )


def _publish(application_id: str, stage_results: dict):
    event_publisher.publish(
        stream="loan:events",
        event_type="node.completed",
        payload={
            "application_id": application_id,
            "stage": "lead_qualification",
            "stage_results": stage_results,
        },
    )


async def run_lead_qualification(state: ApplicationState) -> ApplicationState:
    """
    Node 2: lead_qualification
    Simulates document verification: salary slips, ITR, bank statements.
    Outputs: qualification_result (pass|fail|request_info), verified_income, max_eligible_amount.
    """
    application_id = state.get("application_id")

    # Signal the UI that this node is now executing
    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "lead_qualification"},
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
        result = parse_llm_json(response.content[0].text)

        # affordability_ratio comes as a 0–1 decimal from Claude; convert to percentage
        raw_ratio = result.get("affordability_ratio", 0)
        affordability_pct = round(float(raw_ratio) * 100, 1) if raw_ratio <= 1 else round(float(raw_ratio), 1)

        stage_result = {
            "qualification_result": result.get("qualification_result"),
            "qualification_notes": result.get("qualification_notes"),
            "verified_income": result.get("verified_income"),
            "max_eligible_amount": result.get("max_eligible_amount"),
            "income_consistency": result.get("income_consistency"),
            "affordability_ratio": affordability_pct,
            "document_issues": result.get("document_issues", []),
            **metrics,
        }

        updated_state = {
            **state,
            "current_stage": "lead_qualification",
            "qualification_result": result.get("qualification_result", "fail"),
            "qualification_notes": result.get("qualification_notes", ""),
            "verified_income": float(result.get("verified_income", 0)),
            "max_eligible_amount": float(result.get("max_eligible_amount", 0)),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_qualification": stage_result,
            },
        }
        _publish(application_id, updated_state["stage_results"])
        return updated_state

    except Exception as e:
        logger.error("lead_qualification failed for %s: %s", application_id, e)
        error_state = {
            **state,
            "current_stage": "lead_qualification",
            "qualification_result": "fail",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"lead_qualification: {e}"],
        }
        # Always publish so the UI advances even on failure
        _publish(application_id, error_state.get("stage_results", {}))
        return error_state
