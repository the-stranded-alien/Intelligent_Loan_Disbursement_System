from config.settings import settings


class OCRService:
    """Google Document AI OCR integration."""

    async def process_document(self, file_bytes: bytes, mime_type: str) -> dict:
        """
        Send document to Google Document AI, return extracted fields and confidence.
        """
        # TODO: Initialize DocumentProcessorServiceClient, send process request,
        #       parse Document proto response, extract key-value pairs
        pass

    def extract_fields(self, doc_proto) -> dict:
        """Parse Document AI response proto into a flat field dictionary."""
        # TODO: Iterate doc_proto.pages and entities, build field dict
        pass


ocr_service = OCRService()
