import uuid

from pydantic import BaseModel, EmailStr


class SessionInviteRequest(BaseModel):
    job_id: uuid.UUID
    candidate_name: str
    candidate_email: EmailStr


class SessionInviteResponse(BaseModel):
    session_id: uuid.UUID
    candidate_url: str
    expires_in: str = "48h"


class SessionStartRequest(BaseModel):
    resume_id: uuid.UUID


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    message: str
