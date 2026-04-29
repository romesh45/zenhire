import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import set_session_state
from app.core.security import get_current_recruiter
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.models.resume import Resume
from app.models.session import Session as InterviewSession
from app.schemas.session import (
    SessionInviteRequest,
    SessionInviteResponse,
    SessionStartRequest,
    SessionStartResponse,
)
from app.services.embedding_service import cosine_similarity, generate_embedding
from app.services.pdf_parser import extract_text_from_pdf

router = APIRouter()


@router.post("/invite", response_model=SessionInviteResponse)
async def create_invite(
    payload: SessionInviteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    recruiter: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> SessionInviteResponse:
    job = await db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    session_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    candidate_url = f"https://zenhire.app/interview/{session_id}"

    session = InterviewSession(
        id=session_id,
        job_id=payload.job_id,
        created_by_recruiter_id=recruiter.id,
        candidate_name=payload.candidate_name,
        candidate_email=payload.candidate_email,
        candidate_url=candidate_url,
        status="pending",
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()

    return SessionInviteResponse(session_id=session_id, candidate_url=candidate_url)


@router.post("/{session_id}/start", response_model=SessionStartResponse)
async def start_session(
    session_id: uuid.UUID,
    payload: SessionStartRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionStartResponse:
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is already '{session.status}', cannot start",
        )

    result = await db.execute(
        select(Resume).where(
            Resume.id == payload.resume_id,
            Resume.session_id == session_id,
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found for this session",
        )

    job = await db.get(Job, session.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Extract text and run Resume Agent
    pdf_text = extract_text_from_pdf(resume.pdf_data)

    from app.agents.resume_agent import run_resume_agent
    from app.agents.interview_agent import run_interview_agent

    agent_result = await run_resume_agent(pdf_text, job)

    # Generate embeddings and compute job fit score
    resume_embedding = await generate_embedding(pdf_text)
    job_text = f"{job.title}\n{job.description or ''}\n{' '.join(job.required_skills or [])}"
    job_embedding = await generate_embedding(job_text)
    fit_score = cosine_similarity(resume_embedding, job_embedding)

    # Persist analysis on resume
    resume.resume_structured = agent_result
    resume.resume_score = agent_result["resume_score"]
    resume.skill_gaps = agent_result["skill_gaps"]
    resume.job_fit_score = fit_score
    resume.skill_vector = resume_embedding  # type: ignore[assignment]

    # Run Interview Agent — generates 6 targeted questions
    question_plan = await run_interview_agent(job, agent_result)

    # Advance session
    session.status = "active"
    await db.flush()

    # Warm Redis with full session state including question plan
    await set_session_state(
        session_id,
        {
            "session_id": str(session_id),
            "job_id": str(session.job_id),
            "resume_score": agent_result["resume_score"],
            "skill_gaps": agent_result["skill_gaps"],
            "current_q_index": 0,
            "current_followup_count": 0,
            "answers": [],
            "question_plan": question_plan,
            "status": "active",
        },
    )

    return SessionStartResponse(
        session_id=session_id,
        status="active",
        message=f"Session started. Resume analysed. {len(question_plan)} questions ready.",
    )
