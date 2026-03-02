class ApplicationHandler:
    """Handles application lifecycle notification events."""

    async def on_application_received(self, event: dict) -> None:
        # TODO: Extract applicant data, enqueue notify_application_received task
        pass

    async def on_application_approved(self, event: dict) -> None:
        # TODO: Extract sanction terms, enqueue notify_application_approved task
        pass

    async def on_application_rejected(self, event: dict) -> None:
        # TODO: Extract rejection reason, enqueue notify_application_rejected task
        pass
