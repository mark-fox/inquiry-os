from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnswerRead(BaseModel):
    id: UUID
    run_id: UUID
    content: str
    citations: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)