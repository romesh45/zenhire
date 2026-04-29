from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("session_id", name="uq_reports_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    interview_score: Mapped[float] = mapped_column(Float, nullable=False)
    resume_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    borderline: Mapped[bool] = mapped_column(nullable=False, default=False)
    floor_override: Mapped[bool] = mapped_column(nullable=False, default=False)
    hallucination_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bluff_carry: Mapped[bool] = mapped_column(nullable=False, default=False)

    full_report: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
