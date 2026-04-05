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


async def run_lead_qualification(state: ApplicationState) -> ApplicationState:
    """
    Node 2: lead_qualification
    Simulates document verification: salary slips, ITR, bank statements.
    Outputs: qualification_result (pass|fail|request_info), verified_income, max_eligible_amount.
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
            "current_stage": "lead_qualification",
            "qualification_result": result.get("qualification_result", "fail"),
            "qualification_notes": result.get("qualification_notes", ""),
            "verified_income": float(result.get("verified_income", 0)),
            "max_eligible_amount": float(result.get("max_eligible_amount", 0)),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_qualification": {
                    "qualification_result": result.get("qualification_result"),
                    "qualification_notes": result.get("qualification_notes"),
                    "verified_income": result.get("verified_income"),
                    "max_eligible_amount": result.get("max_eligible_amount"),
                    "income_consistency": result.get("income_consistency"),
                    "affordability_ratio": result.get("affordability_ratio"),
                    "document_issues": result.get("document_issues", []),
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "lead_qualification",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("lead_qualification failed for %s: %s", state.get("application_id"), e)
        return {
            **state,
            "current_stage": "lead_qualification",
            "qualification_result": "fail",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"lead_qualification: {e}"],
        }
