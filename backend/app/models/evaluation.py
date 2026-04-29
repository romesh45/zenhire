import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(10), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    followup_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dimension scores (None until evaluator completes)
    technical_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_of_explanation: Mapped[float | None] = mapped_column(Float, nullable=True)
    problem_solving: Mapped[float | None] = mapped_column(Float, nullable=True)
    communication_clarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning_quality: Mapped[float | None] = mapped_column(Float, nullable=True)

    hallucination_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    audit_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    recruiter_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    eval_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending | complete | failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
