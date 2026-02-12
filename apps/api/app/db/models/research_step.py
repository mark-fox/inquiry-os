import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchStepType(str, enum.Enum):
    PLANNER = "planner"
    SEARCHER = "searcher"
    READER = "reader"
    SYNTHESIZER = "synthesizer"


class ResearchStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    
class ResearchStep(Base):
    __tablename__ = "research_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    step_index: Mapped[int] = mapped_column(Integer, nullable=False)

    step_type: Mapped[ResearchStepType] = mapped_column(
        Enum(ResearchStepType, name="research_step_type"),
        nullable=False,
    )

    status: Mapped[ResearchStepStatus] = mapped_column(
        Enum(ResearchStepStatus, name="research_step_status"),
        nullable=False,
        default=ResearchStepStatus.PENDING,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(back_populates="steps")
