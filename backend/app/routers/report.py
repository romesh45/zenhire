from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_recruiter
from app.engine.decision import DecisionEngine
from app.models.evaluation import Evaluation
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.models.report import Report
from app.models.resume import Resume
from app.models.session import Session as InterviewSession
from app.schemas.report import DecisionReport, DimensionAverages, ReportResponse

router = APIRouter()
_engine = DecisionEngine()


@router.post("/{session_id}/evaluate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    recruiter: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> ReportResponse:
    # Auth guard: recruiter must own this session
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.created_by_recruiter_id != recruiter.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Session must be completed
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is '{session.status}' — must be 'completed' before generating report",
        )

    # Block if any evaluations still pending
    pending_result = await db.execute(
        select(Evaluation).where(
            Evaluation.session_id == session_id,
            Evaluation.eval_status == "pending",
        )
    )
    if pending_result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluations still in progress — retry once all answers are scored",
        )

    # Load completed evaluations
    evals_result = await db.execute(
        select(Evaluation).where(
            Evaluation.session_id == session_id,
            Evaluation.eval_status == "complete",
        )
    )
    evaluations = evals_result.scalars().all()

    eval_dicts = [
        {
            "technical_accuracy": ev.technical_accuracy,
            "depth_of_explanation": ev.depth_of_explanation,
            "problem_solving": ev.problem_solving,
            "communication_clarity": ev.communication_clarity,
            "relevance": ev.relevance,
            "reasoning_quality": ev.reasoning_quality,
            "hallucination_flags": ev.hallucination_flags or [],
        }
        for ev in evaluations
    ]

    # Load resume_score
    resume_result = await db.execute(
        select(Resume).where(Resume.session_id == session_id)
    )
    resume = resume_result.scalars().first()
    resume_score = float(resume.resume_score or 0.0) if resume else 0.0

    # Load job for dimension_weights
    job = await db.get(Job, session.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_dict = {
        "title": job.title,
        "dimension_weights": job.dimension_weights or {},
    }

    # Run Decision Engine (may raise ValueError for incomplete_session)
    try:
        report_data = _engine.compute(eval_dicts, resume_score, job_dict)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Upsert report (unique on session_id)
    existing = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report_row = existing.scalars().first()

    if report_row is None:
        report_row = Report(
            session_id=session_id,
            tier=report_data["tier"],
            final_score=report_data["final_score"],
            interview_score=report_data["interview_score"],
            resume_score=report_data["resume_score"],
            confidence=report_data["confidence"],
            borderline=report_data["borderline"],
            floor_override=report_data["floor_override"],
            hallucination_penalty=report_data["hallucination_penalty"],
            bluff_carry=report_data["bluff_carry"],
            full_report=report_data,
        )
        db.add(report_row)
    else:
        report_row.tier = report_data["tier"]
        report_row.final_score = report_data["final_score"]
        report_row.interview_score = report_data["interview_score"]
        report_row.resume_score = report_data["resume_score"]
        report_row.confidence = report_data["confidence"]
        report_row.borderline = report_data["borderline"]
        report_row.floor_override = report_data["floor_override"]
        report_row.hallucination_penalty = report_data["hallucination_penalty"]
        report_row.bluff_carry = report_data["bluff_carry"]
        report_row.full_report = report_data

    await db.flush()
    await db.refresh(report_row)

    return _build_response(report_row, report_data)


@router.get("/{session_id}/report", response_model=ReportResponse)
async def get_report(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    recruiter: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> ReportResponse:
    # Auth guard
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.created_by_recruiter_id != recruiter.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    report_row = result.scalars().first()
    if report_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not generated yet — call POST /sessions/{id}/evaluate first",
        )

    report_data = report_row.full_report
    return _build_response(report_row, report_data)


def _build_response(report_row: Report, report_data: dict) -> ReportResponse:
    dim = report_data["dimension_averages"]
    decision = DecisionReport(
        tier=report_data["tier"],
        final_score=report_data["final_score"],
        interview_score=report_data["interview_score"],
        resume_score=report_data["resume_score"],
        dimension_averages=DimensionAverages(
            technical_accuracy=dim["technical_accuracy"],
            depth_of_explanation=dim["depth_of_explanation"],
            problem_solving=dim["problem_solving"],
            communication_clarity=dim["communication_clarity"],
            relevance=dim["relevance"],
            reasoning_quality=dim["reasoning_quality"],
        ),
        floor_violations=report_data["floor_violations"],
        floor_override=report_data["floor_override"],
        hallucination_penalty=report_data["hallucination_penalty"],
        bluff_carry=report_data["bluff_carry"],
        confidence=report_data["confidence"],
        borderline=report_data["borderline"],
        evaluated_at=report_data["evaluated_at"],
    )
    return ReportResponse(
        report_id=report_row.id,
        session_id=report_row.session_id,
        created_at=report_row.created_at,
        report=decision,
    )
