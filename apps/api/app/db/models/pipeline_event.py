import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PipelineEventType(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(str, enum.Enum):
    DUMMY = "dummy"
    REAL = "real"


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

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

    event_type: Mapped[PipelineEventType] = mapped_column(
        Enum(PipelineEventType, name="pipeline_event_type"),
        nullable=False,
    )

    mode: Mapped[ExecutionMode] = mapped_column(
        Enum(ExecutionMode, name="execution_mode"),
        nullable=False,
    )

    stage: Mapped[str | None] = mapped_column(String(length=50), nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped["ResearchRun"] = relationship(back_populates="events")