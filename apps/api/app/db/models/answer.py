import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_answers_run_id"),
    )

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

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Citations map tokens -> list of source IDs, e.g. { "S1": ["uuid1"] }
    citations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship(back_populates="answer")
