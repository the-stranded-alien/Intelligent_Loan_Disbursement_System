class DocumentHandler:
    """Handles document collection notification events."""

    async def on_documents_required(self, event: dict) -> None:
        # TODO: Extract missing documents list, enqueue notify_document_reminder task
        pass

    async def on_documents_verified(self, event: dict) -> None:
        # TODO: Optionally notify applicant that documents were accepted
        pass
