class SanctionHandler:
    """Handles sanction processing notification events."""

    async def on_sanction_issued(self, event: dict) -> None:
        # TODO: Send sanction letter via email + WhatsApp with e-sign link
        pass

    async def on_sanction_accepted(self, event: dict) -> None:
        # TODO: Notify internal team and trigger disbursement flow
        pass

    async def on_sanction_expired(self, event: dict) -> None:
        # TODO: Notify applicant that sanction letter has expired
        pass
