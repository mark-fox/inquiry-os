import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    query: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(length=255), nullable=True)

    status: Mapped[ResearchRunStatus] = mapped_column(
        Enum(ResearchRunStatus, name="research_run_status"),
        nullable=False,
        default=ResearchRunStatus.PENDING,
    )

    model_provider: Mapped[str] = mapped_column(
        String(length=100),
        nullable=False,
        default="ollama:llama3",
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    steps: Mapped[list["ResearchStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ResearchStep.step_index",
    )

    sources: Mapped[list["Source"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    answer: Mapped["Answer | None"] = relationship(
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )
