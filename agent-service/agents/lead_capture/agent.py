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

AGENT_ROLE = "critic"  # Validates/screens raw form input

_PROMPT_PATH = Path(__file__).parent.parent.parent / "config" / "prompts" / "lead_capture.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        phone=state.get("phone", ""),
        email=state.get("email", ""),
        pan_number=state.get("pan_number", ""),
        date_of_birth=state.get("date_of_birth", ""),
        city=state.get("city", ""),
        state=state.get("state", ""),
        residential_status=state.get("residential_status", ""),
        years_at_current_address=state.get("years_at_current_address", 0),
        employment_type=state.get("employment_type", "salaried"),
        employer_name=state.get("employer_name", ""),
        years_in_current_job=state.get("years_in_current_job", 0),
        monthly_income=state.get("monthly_income", 0),
        existing_emi_amount=state.get("existing_emi_amount", 0),
        loan_amount=state.get("loan_amount", 0),
        loan_purpose=state.get("loan_purpose", ""),
        tenure_months=state.get("tenure_months", 12),
    )


async def run_lead_capture(state: ApplicationState) -> ApplicationState:
    """
    Node 1: lead_capture
    Validates web form fields against basic eligibility rules (age, PAN format,
    income, loan limits). Does NOT check documents or credit — that is downstream.
    Outputs: eligibility_result (eligible|ineligible), eligibility_reason.
    """
    application_id = state.get("application_id")
    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "lead_capture"},
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

        updated_state = {
            **state,
            "current_stage": "lead_capture",
            "eligibility_result": result.get("eligibility_result", "ineligible"),
            "eligibility_reason": result.get("eligibility_reason", ""),
            "data_quality_issues": result.get("data_quality_issues", []),
            "lead_source": result.get("lead_source", "web"),
            "phone": result.get("normalized_phone", state.get("phone", "")),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_capture": {
                    "eligibility_result": result.get("eligibility_result"),
                    "eligibility_reason": result.get("eligibility_reason"),
                    "applicant_age": result.get("applicant_age"),
                    "data_quality_issues": result.get("data_quality_issues", []),
                    "residential_stability": result.get("residential_stability"),
                    "employment_stability": result.get("employment_stability"),
                    **metrics,
                },
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "lead_capture",
                "stage_results": updated_state["stage_results"],
            },
        )
        return updated_state

    except Exception as e:
        logger.error("lead_capture failed for %s: %s", state.get("application_id"), e)
        error_state = {
            **state,
            "current_stage": "lead_capture",
            "eligibility_result": "ineligible",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"lead_capture: {e}"],
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "lead_capture",
                "stage_results": error_state.get("stage_results", {}),
            },
        )
        return error_state
