import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    resume_structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resume_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_gaps: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    job_fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_vector: Mapped[list | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
