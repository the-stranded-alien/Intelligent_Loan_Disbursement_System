import json
import logging
import re
from pathlib import Path

import anthropic
from jinja2 import Template

from graph.state import ApplicationState
from config.settings import settings
from agents.lead_qualification.tools import check_eligibility_criteria

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / \
    "config" / "prompts" / "lead_qualification.j2"

ELIGIBILITY_POLICY = """
LOANFLOW LENDING POLICY - ELIGIBILITY CRITERIA v2.1

1. AGE
   - Minimum age: 21 years
   - Maximum age: 60 years for salaried, 65 for self-employed

2. INCOME THRESHOLDS
   - Salaried:      minimum monthly income Rs.30,000
   - Self-employed: minimum monthly income Rs.50,000

3. LOAN AMOUNT LIMITS
   - Minimum: Rs.10,000
   - Maximum: Rs.50,00,000
   - Must not exceed 10x monthly income

4. LOAN PURPOSE
   - Approved: Home Renovation, Education, Medical, Business,
     Vehicle, Wedding, Travel, Other
   - Rejected: Gambling, Speculative investment, Illegal activities

5. PAN VALIDATION
   - Must be present and valid format e.g. ABCDE1234F

6. CONTACT
   - Valid 10-digit Indian mobile number required

7. LEAD SCORE
   - Below 30: auto-reject
   - 30-49:    borderline, use judgment
   - 50+:      proceed normally
"""


def _render_prompt(state: ApplicationState, eligibility_result: dict) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        phone=state.get("phone", ""),
        email=state.get("email", ""),
        pan_number=state.get("pan_number", ""),
        date_of_birth=state.get("date_of_birth", ""),
        employment_type=state.get("employment_type", ""),
        monthly_income=state.get("monthly_income"),
        loan_amount=state.get("loan_amount", 0),
        loan_purpose=state.get("loan_purpose", ""),
        tenure_months=state.get("tenure_months", 12),
        lead_score=state.get("lead_score", 0),
        lead_source=state.get("lead_source", "web"),
        passed_checks=eligibility_result.get("passed", []),
        failed_checks=eligibility_result.get("failed", []),
        disqualification_reasons=eligibility_result.get(
            "disqualification_reasons", []),
        policy_context=ELIGIBILITY_POLICY,
    )


def _parse_response(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_lead_qualification(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_qualification (Stage 2)

    Flow:
      1. Run deterministic eligibility checks including age, income, PAN
      2. Hard fail fields --> reject without calling Claude
      3. Otherwise --> call Claude for final judgment
    """
    logger.info("Lead qualification for %s", state.get("application_id"))

    # Step 1: Deterministic checks
    eligibility = check_eligibility_criteria(state)
    logger.info(
        "Passed=%s  Failed=%s",
        eligibility["passed"],
        eligibility["failed"],
    )

    # Step 2: Hard fail -- reject without calling Claude
    hard_fail_fields = [
        "full_name",
        "pan_number",
        "phone",
        "loan_amount_min",
        "loan_amount_max",
        "age_too_young",
        "age_too_old",
        "loan_purpose",
    ]
    hard_failed = [
        f for f in eligibility.get("failed", [])
        if f in hard_fail_fields
    ]

    if hard_failed:
        logger.info("Hard fail on %s -- rejecting without LLM", hard_failed)
        return {
            **state,
            "current_stage":            "lead_qualification",
            "qualification_result":     "rejected",
            "qualification_notes":      (
                "Rejected at eligibility check: "
                + ", ".join(eligibility["disqualification_reasons"])
            ),
            "disqualification_reasons": eligibility["disqualification_reasons"],
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_qualification": {
                    "method":        "hard_fail",
                    "failed_checks": eligibility["failed"],
                },
            },
        }

    # Step 3: Call Claude for final decision
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _render_prompt(state, eligibility)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        result = _parse_response(raw)
        q = result.get("qualification_result", "rejected")

        logger.info(
            "Claude decision for %s: %s",
            state.get("application_id"), q,
        )

        return {
            **state,
            "current_stage":            "lead_qualification",
            "qualification_result":     q,
            "qualification_notes":      result.get("qualification_notes", ""),
            "disqualification_reasons": result.get("disqualification_reasons", []),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_qualification": {
                    "method":             "llm",
                    "risk_level":         result.get("risk_level"),
                    "recommended_action": result.get("recommended_action"),
                    "passed_checks":      eligibility["passed"],
                    "failed_checks":      eligibility["failed"],
                },
            },
        }

    except Exception as e:
        logger.error(
            "lead_qualification error for %s: %s",
            state.get("application_id"), e,
        )
        return {
            **state,
            "current_stage":        "lead_qualification",
            "qualification_result": "rejected",
            "qualification_notes":  f"System error: {e}",
            "pipeline_errors": [
                *state.get("pipeline_errors", []),
                f"lead_qualification: {e}",
            ],
        }
