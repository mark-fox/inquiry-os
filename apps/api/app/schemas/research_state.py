from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.db.models import ResearchRunStatus, ResearchStepStatus, ResearchStepType


class StepState(BaseModel):
    status: ResearchStepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ResearchRunState(BaseModel):
    run_id: UUID
    status: ResearchRunStatus
    steps: dict[ResearchStepType, StepState]
    source_count: int
    sources_with_summary: int