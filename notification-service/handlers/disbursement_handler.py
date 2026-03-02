class DisbursementHandler:
    """Handles disbursement notification events."""

    async def on_disbursement_initiated(self, event: dict) -> None:
        # TODO: Enqueue notify_disbursement_initiated task
        pass

    async def on_disbursement_success(self, event: dict) -> None:
        # TODO: Enqueue notify_disbursement_success task
        pass

    async def on_disbursement_failed(self, event: dict) -> None:
        # TODO: Notify applicant of delay and expected retry time
        pass
