import json
import logging

import anthropic

from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher
from services.json_parser import parse_llm_json
from agents.credit_assessment.tools import CIBIL_TOOL_SCHEMA, mock_cibil_lookup

logger = logging.getLogger(__name__)

AGENT_ROLE = "analyst"

_SYSTEM_PROMPT = """\
You are a credit underwriting analyst. Your job is to assess loan applications using real credit bureau data.

You MUST call the mock_cibil_lookup tool with the applicant's PAN number before making any decision.
Once you have the bureau result, combine it with the applicant's financial profile to produce your assessment.

Decision rules:
- Score ≥ 750 AND overdue = 0           → approve (risk_grade A)
- Score 700–749 AND overdue ≤ 1         → approve (risk_grade B)
- Score 650–699                          → approve with reduced amount (risk_grade C)
- Score 600–649 AND overdue ≥ 2         → reject
- Score < 600                            → reject
- DTI (existing_emi / monthly_income) > 0.6 → reject regardless of score

Suggested loan amount:
- Grade A: min(requested, max_eligible)
- Grade B: min(requested, max_eligible × 0.9)
- Grade C: min(requested, max_eligible × 0.75)
- Rejected: 0

After receiving the tool result, respond with ONLY a JSON object (no prose):
{
  "credit_score": <integer from tool>,
  "credit_decision": "<approve|reject>",
  "repayment_history": "<good|fair|poor>",
  "suggested_loan_amount": <number>,
  "dti_ratio": <existing_emi / monthly_income, decimal>,
  "risk_grade": "<A|B|C|D>",
  "credit_notes": "<one sentence underwriting rationale citing the bureau score>"
}
"""


def _user_message(state: ApplicationState) -> str:
    verified_income = state.get("verified_income") or state.get("monthly_income", 0)
    existing_emi = state.get("existing_emi_amount", 0)
    max_eligible = state.get("max_eligible_amount") or state.get("loan_amount", 0)
    return (
        f"Applicant: {state.get('full_name', '')}\n"
        f"PAN: {state.get('pan_number', '')}\n"
        f"Employment: {state.get('employment_type', 'salaried')}\n"
        f"Verified Monthly Income: ₹{verified_income}\n"
        f"Existing EMI: ₹{existing_emi}\n"
        f"Loan Requested: ₹{state.get('loan_amount', 0)} for {state.get('tenure_months', 12)} months\n"
        f"Purpose: {state.get('loan_purpose', '')}\n"
        f"Max Eligible Amount (from doc check): ₹{max_eligible}\n\n"
        f"Please call mock_cibil_lookup with the PAN number now."
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
    Uses Claude tool_use to call mock_cibil_lookup(pan_number), then produces
    a structured credit decision. Each applicant gets a deterministic, differentiated score.
    """
    application_id = state.get("application_id")

    event_publisher.publish(
        stream="loan:events",
        event_type="node.started",
        payload={"application_id": application_id, "stage": "credit_assessment"},
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    messages = [{"role": "user", "content": _user_message(state)}]

    try:
        # ── Turn 1: Claude calls the CIBIL tool ───────────────────────────────
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[CIBIL_TOOL_SCHEMA],
            messages=messages,
        )

        # Extract tool call and execute it
        tool_use_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None,
        )

        if tool_use_block:
            pan = tool_use_block.input.get("pan_number", state.get("pan_number", ""))
            cibil_result = mock_cibil_lookup(pan)
            logger.info("CIBIL lookup for %s: score=%s", pan, cibil_result["credit_score"])

            # ── Turn 2: feed tool result back, get final JSON decision ────────
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": json.dumps(cibil_result),
                    }
                ],
            })

            final_response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                tools=[CIBIL_TOOL_SCHEMA],
                messages=messages,
            )
            result_text = next(
                (b.text for b in final_response.content if hasattr(b, "text")),
                "{}",
            )
        else:
            # Claude skipped the tool — use whatever text it returned directly
            result_text = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "{}",
            )
            cibil_result = {}

        result = parse_llm_json(result_text)

        # dti_ratio: normalise to percentage for UI
        raw_dti = result.get("dti_ratio", 0)
        dti_pct = round(float(raw_dti) * 100, 1) if float(raw_dti) <= 1 else round(float(raw_dti), 1)

        stage_result = {
            "credit_score": result.get("credit_score") or cibil_result.get("credit_score"),
            "credit_decision": result.get("credit_decision"),
            "suggested_loan_amount": result.get("suggested_loan_amount"),
            "repayment_history": result.get("repayment_history"),
            "dti_ratio": dti_pct,
            "risk_grade": result.get("risk_grade"),
            "credit_notes": result.get("credit_notes"),
            # Raw bureau data for audit trail
            "bureau_active_loans": cibil_result.get("active_loan_count"),
            "bureau_overdue_payments": cibil_result.get("overdue_payments_last_12m"),
            "bureau_credit_age_months": cibil_result.get("credit_age_months"),
        }

        updated_state = {
            **state,
            "current_stage": "credit_assessment",
            "credit_score": int(result.get("credit_score") or cibil_result.get("credit_score", 600)),
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
