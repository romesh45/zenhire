import uuid

from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    resume_id: uuid.UUID
    filename: str
    session_id: uuid.UUID


class ResumeAnalysisResponse(BaseModel):
    resume_id: uuid.UUID
    skills_found: list[str]
    skill_gaps: list[str]
    resume_score: float
    job_fit_score: float | None
