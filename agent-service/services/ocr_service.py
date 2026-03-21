import base64
import json
import re
import logging
import anthropic
from config.settings import settings

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7

EXTRACTION_PROMPT = (
    "You are a document extraction specialist for a loan processing system. "
    "A branch staff member has scanned a physical loan application form. "
    "Extract all the fields from this form image.\n\n"
    "Extract these fields if visible:\n"
    "- full_name: applicant full name\n"
    "- phone: mobile number 10 digits\n"
    "- email: email address\n"
    "- pan_number: PAN card number format ABCDE1234F\n"
    "- loan_amount: amount in INR numbers only no symbols\n"
    "- loan_purpose: purpose of the loan\n"
    "- tenure_months: loan tenure in months number only\n"
    "- date_of_birth: date of birth DD/MM/YYYY\n\n"
    "Rules:\n"
    "- If a field is unclear or not present set value to null\n"
    "- For loan_amount return only the number e.g. 500000 not Rs.5,00,000\n"
    "- For pan_number return uppercase e.g. ABCDE1234F\n"
    "- For phone return 10 digits only strip +91 or 0 prefix\n"
    "- Give a confidence score 0.0-1.0 for each field\n"
    "- Give an overall confidence score 0.0-1.0\n\n"
    "Respond with JSON only inside triple backticks.\n\n"
    "```json\n"
    "{\n"
    "  \"fields\": {\n"
    "    \"full_name\":     { \"value\": \"<string or null>\", \"confidence\": 0.0 },\n"
    "    \"phone\":         { \"value\": \"<string or null>\", \"confidence\": 0.0 },\n"
    "    \"email\":         { \"value\": \"<string or null>\", \"confidence\": 0.0 },\n"
    "    \"pan_number\":    { \"value\": \"<string or null>\", \"confidence\": 0.0 },\n"
    "    \"loan_amount\":   { \"value\": null,                \"confidence\": 0.0 },\n"
    "    \"loan_purpose\":  { \"value\": \"<string or null>\", \"confidence\": 0.0 },\n"
    "    \"tenure_months\": { \"value\": null,                \"confidence\": 0.0 },\n"
    "    \"date_of_birth\": { \"value\": \"<string or null>\", \"confidence\": 0.0 }\n"
    "  },\n"
    "  \"overall_confidence\": 0.0,\n"
    "  \"extraction_notes\": \"<any issues or observations>\"\n"
    "}\n"
    "```"
)


class OCRService:
    """
    Vision LLM-based form extraction.
    Uses Claude claude-sonnet-4-6 to read scanned loan application forms
    and extract structured fields — no Google Document AI needed.
    """

    async def process_document(self, file_bytes: bytes, mime_type: str) -> dict:
        """
        Send scanned form image to Claude claude-sonnet-4-6 vision.
        Returns extracted fields with confidence scores.
        """
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"

        image_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

        client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": mime_type,
                                "data":       image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }],
            )
            raw = response.content[0].text
            result = self._parse_response(raw)

            return {
                "status":     "success",
                "fields":     result.get("fields", {}),
                "confidence": result.get("overall_confidence", 0.0),
                "notes":      result.get("extraction_notes", ""),
            }

        except Exception as e:
            logger.error("Claude OCR failed: %s", e)
            return {
                "status":     "failed",
                "error":      str(e),
                "fields":     {},
                "confidence": 0.0,
                "notes":      "",
            }

    def _parse_response(self, text: str) -> dict:
        """Extract JSON block from Claude response."""
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)

    def to_application_state(self, ocr_result: dict) -> dict:
        """
        Convert OCR result into ApplicationState-compatible dict.
        Only maps fields with confidence >= CONFIDENCE_THRESHOLD.
        """
        if ocr_result.get("status") != "success":
            return {}

        state = {}
        fields = ocr_result.get("fields", {})

        for key in ["full_name", "phone", "email", "pan_number",
                    "loan_purpose", "date_of_birth"]:
            if key in fields:
                d = fields[key]
                if d.get("value") and d.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
                    state[key] = d["value"]

        if "loan_amount" in fields:
            d = fields["loan_amount"]
            if d.get("value") and d.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
                try:
                    state["loan_amount"] = float(d["value"])
                except (ValueError, TypeError):
                    pass

        if "tenure_months" in fields:
            d = fields["tenure_months"]
            if d.get("value") and d.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
                try:
                    state["tenure_months"] = int(d["value"])
                except (ValueError, TypeError):
                    pass

        return state


ocr_service = OCRService()
