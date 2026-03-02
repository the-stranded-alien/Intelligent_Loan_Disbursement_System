from langchain_core.tools import tool


@tool
def verify_pan(pan_number: str, name: str) -> dict:
    """Verify PAN card via NSDL/UTIITSL API."""
    # TODO: Call PAN verification API, return status and name match score
    pass


@tool
def verify_aadhaar(aadhaar_number: str, otp: str) -> dict:
    """Verify Aadhaar via UIDAI API (OTP-based)."""
    # TODO: Call UIDAI API, return verification status
    pass


@tool
def ocr_document(document_path: str, document_type: str) -> dict:
    """Run Google Document AI OCR on an uploaded document."""
    # TODO: Call ocr_service, return extracted fields and confidence scores
    pass
