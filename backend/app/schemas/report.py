from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class HallucinationSummary(BaseModel):
    total_flags: int
    flag_counts: dict[str, int]


class DimensionAverages(BaseModel):
    technical_accuracy: float
    depth_of_explanation: float
    problem_solving: float
    communication_clarity: float
    relevance: float
    reasoning_quality: float


class DecisionReport(BaseModel):
    tier: str
    final_score: float
    interview_score: float
    resume_score: float
    dimension_averages: DimensionAverages
    floor_violations: list[str]
    floor_override: bool
    hallucination_penalty: float
    bluff_carry: bool
    confidence: float
    borderline: bool
    evaluated_at: str


class ReportResponse(BaseModel):
    report_id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
    report: DecisionReport

    model_config = {"from_attributes": True}
