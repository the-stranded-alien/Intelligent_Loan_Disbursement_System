import json
import logging
import re
from pathlib import Path

import anthropic
from jinja2 import Template
from config.settings import settings
from services.ocr_service import ocr_service
from graph.state import ApplicationState
from config.settings import settings
from services.event_publisher import event_publisher

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / \
    "config" / "prompts" / "lead_capture.j2"


def _render_prompt(state: ApplicationState) -> str:
    template = Template(_PROMPT_PATH.read_text())
    return template.render(
        full_name=state.get("full_name", ""),
        phone=state.get("phone", ""),
        email=state.get("email", ""),
        pan_number=state.get("pan_number", ""),
        loan_amount=state.get("loan_amount", 0),
        loan_purpose=state.get("loan_purpose", ""),
        tenure_months=state.get("tenure_months", 12),
        # Branch fields  — None for web portal leads
        lead_source=state.get("lead_source", "web"),
        branch_code=state.get("branch_code"),
        branch_name=state.get("branch_name"),
        staff_name=state.get("staff_name"),
        staff_id=state.get("staff_id"),
        kyc_physically_seen=state.get("kyc_physically_seen", False),
        customer_consent_signed=state.get("customer_consent_signed", False),
        # OCR fields  — None for web and typed branch leads
        ocr_confidence=state.get("ocr_confidence"),
        ocr_extraction_status=state.get("ocr_extraction_status"),
    )


def _parse_response(text: str) -> dict:
    """Extract JSON from Claude's response."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


async def run_lead_capture(state: ApplicationState) -> ApplicationState:
    """
    Node: lead_capture
    Handles all 3 lead sources:
      - web portal     → state has full_name, phone etc. already filled
      - branch typed   → same as web but with branch fields set
      - branch scanned → scanned_document_path set, OCR runs first
    """

    # ── OCR: only runs for scanned paper forms ────────────────────────
    # Web portal and typed branch leads skip this block entirely
    scanned_path = state.get("scanned_document_path")
    scanned_mime = state.get("scanned_document_mime", "image/jpeg")

    if scanned_path:
        logger.info("Scanned document found — running OCR for %s",
                    state.get("application_id"))
        try:
            with open(scanned_path, "rb") as f:
                file_bytes = f.read()

            ocr_result = await ocr_service.process_document(file_bytes, scanned_mime)
            extracted = ocr_service.to_application_state(ocr_result)

            # Only overwrite fields that are empty or PENDING_OCR
            for field, value in extracted.items():
                existing = state.get(field)
                if not existing or existing == "PENDING_OCR":
                    state = {**state, field: value}

            # Store OCR metadata in state
            state = {
                **state,
                "ocr_extraction_status": ocr_result.get("status"),
                "ocr_confidence":        ocr_result.get("confidence"),
                "ocr_extracted_fields":  ocr_result.get("fields", {}),
            }
            logger.info("OCR complete — confidence: %.0f%%",
                        (ocr_result.get("confidence", 0) * 100))

        except Exception as e:
            logger.error("OCR failed for %s: %s",
                         state.get("application_id"), e)
            state = {
                **state,
                "ocr_extraction_status": "failed",
                "pipeline_errors": [
                    *state.get("pipeline_errors", []),
                    f"ocr: {e}",
                ],
            }

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
            "current_stage": "lead_capture",
            "lead_score": float(result.get("lead_score", 50)),
            "lead_source": result.get("lead_source", "web"),
            "phone": result.get("normalized_phone", state.get("phone", "")),
            "stage_results": {
                **state.get("stage_results", {}),
                "lead_capture": result,
            },
        }
        event_publisher.publish(
            stream="loan:events",
            event_type="node.completed",
            payload={
                "application_id": state.get("application_id"),
                "stage": "lead_capture",
                "stage_results": updated_state.get("stage_results", {}),
            },
        )
        return updated_state
    except Exception as e:
        logger.error("lead_capture failed for %s: %s",
                     state.get("application_id"), e)
        return {
            **state,
            "current_stage": "lead_capture",
            "pipeline_errors": [*state.get("pipeline_errors", []), f"lead_capture: {e}"],
        }
