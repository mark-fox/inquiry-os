from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.pipeline_event import PipelineEventType, ExecutionMode


class PipelineEventRead(BaseModel):
    id: UUID
    event_type: PipelineEventType
    mode: ExecutionMode
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}