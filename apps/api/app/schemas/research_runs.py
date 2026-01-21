from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.research_run import ResearchRunStatus
from app.db.models.research_step import ResearchStepType


class ResearchRunBase(BaseModel):
    query: str
    title: str | None = None


class ResearchRunCreate(ResearchRunBase):
    """
    Payload for creating a new research run.
    For now this is just the query (and optional title).
    """
    pass


class ResearchRunRead(BaseModel):
    """
    Minimal representation of a research run returned to the client.
    We'll add nested steps/sources/answers in a 'detail' schema later.
    """

    id: UUID
    query: str
    title: str | None
    status: ResearchRunStatus
    model_provider: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchStepRead(BaseModel):
    id: UUID
    run_id: UUID
    step_index: int
    step_type: ResearchStepType
    input: dict | None
    output: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchRunDetail(ResearchRunRead):
    """
    Detailed view of a research run, including its steps.

    Later we can extend this with sources and answer once those agents
    are implemented.
    """

    steps: list[ResearchStepRead] = []
