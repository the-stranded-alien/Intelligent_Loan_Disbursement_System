class HITLHandler:
    """Handles Human-In-The-Loop (RM review) notification events."""

    async def on_hitl_required(self, event: dict) -> None:
        # TODO: Determine assigned RM, enqueue notify_hitl_pending task
        pass

    async def on_hitl_completed(self, event: dict) -> None:
        # TODO: Notify applicant of RM decision (approval/rejection/more info required)
        pass
