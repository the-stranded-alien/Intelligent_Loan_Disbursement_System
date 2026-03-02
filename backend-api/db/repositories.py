from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Application, Document, RMReview, AuditLog


class ApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Application:
        # TODO: Insert new application record
        pass

    async def get_by_id(self, application_id: str) -> Application | None:
        # TODO: SELECT application by primary key
        pass

    async def update_status(self, application_id: str, status: str, stage: str) -> Application:
        # TODO: UPDATE status and current_stage
        pass

    async def list_all(self, filters: dict) -> list[Application]:
        # TODO: SELECT with optional filters
        pass


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Document:
        # TODO: Insert document record
        pass

    async def get_by_application(self, application_id: str) -> list[Document]:
        # TODO: SELECT documents for application
        pass


class RMReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> RMReview:
        # TODO: Insert RM review record
        pass

    async def get_pending_queue(self) -> list[Application]:
        # TODO: SELECT applications awaiting HITL review
        pass


class AuditLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, application_id: str, event_type: str, actor: str, payload: dict):
        # TODO: Insert audit log entry
        pass
