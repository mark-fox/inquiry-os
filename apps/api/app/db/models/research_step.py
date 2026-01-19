import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchStepType(str, enum.Enum):
    PLANNER = "planner"
    SEARCHER = "searcher"
    READER = "reader"
    SYNTHESIZER = "synthesizer"


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

    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(back_populates="steps")
