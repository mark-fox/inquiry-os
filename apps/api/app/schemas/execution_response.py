from uuid import UUID

from pydantic import BaseModel

from app.db.models import ResearchRunStatus


class ExecutionAccepted(BaseModel):
    run_id: UUID
    status: ResearchRunStatus
    message: str