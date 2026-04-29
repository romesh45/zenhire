import logging
import uuid
from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.arbiter_agent import arbiter_decision, mark_signal_hits
from app.core.database import AsyncSessionLocal, get_db
from app.core.redis_client import get_session_state, set_session_state
from app.core.security import get_current_recruiter
from app.models.evaluation import Evaluation
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.models.session import Session as InterviewSession
from app.schemas.interview import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    EvaluationStatusResponse,
    QuestionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── background evaluator ────────────────────────────────────────────────────

async def _evaluate_answer_bg(
    eval_id: uuid.UUID,
    question: dict,
    answer_text: str,
    job_data: dict,
) -> None:
    """Runs evaluator agent asynchronously and persists scores. Never blocks the response."""
    from app.agents.evaluator_agent import run_evaluator_agent

    job_ns = SimpleNamespace(**job_data)

    async with AsyncSessionLocal() as db:
        try:
            result = await run_evaluator_agent(question, answer_text, job_ns)

            row = await db.get(Evaluation, eval_id)
            if row:
                row.technical_accuracy = result["technical_accuracy"]
                row.depth_of_explanation = result["depth_of_explanation"]
                row.problem_solving = result["problem_solving"]
                row.communication_clarity = result["communication_clarity"]
                row.relevance = result["relevance"]
                row.reasoning_quality = result["reasoning_quality"]
                row.hallucination_flags = result["hallucination_flags"]
                row.audit_trace = result["audit_trace"]
                row.recruiter_summary = result["recruiter_summary"]
                row.eval_status = "complete"
                await db.commit()
                logger.info("Evaluation %s complete", eval_id)
        except Exception as exc:
            logger.error("Evaluator background task failed for eval %s: %s", eval_id, exc)
            try:
                row = await db.get(Evaluation, eval_id)
                if row:
                    row.eval_status = "failed"
                    await db.commit()
            except Exception:
                pass


# ─── helpers ─────────────────────────────────────────────────────────────────

def _to_question_response(q: dict, followup_count: int) -> QuestionResponse:
    return QuestionResponse(
        question_id=q["question_id"],
        question_text=q["question_text"],
        difficulty=q["difficulty"],
        followup_count=followup_count,
    )


async def _load_active_state(session_id: uuid.UUID) -> dict:
    state = await get_session_state(session_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session state not found — session may have expired",
        )
    if state.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is '{state.get('status')}', not active",
        )
    if "question_plan" not in state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not fully initialised — question plan missing",
        )
    return state


# ─── routes ──────────────────────────────────────────────────────────────────

@router.get("/{session_id}/question", response_model=QuestionResponse)
async def get_current_question(session_id: uuid.UUID) -> QuestionResponse:
    state = await _load_active_state(session_id)

    q_index: int = state.get("current_q_index", 0)
    if q_index >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview complete — all questions answered",
        )

    question = state["question_plan"][q_index]
    return _to_question_response(question, state.get("current_followup_count", 0))


@router.post("/{session_id}/answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    session_id: uuid.UUID,
    payload: AnswerSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnswerSubmitResponse:
    # Manual 400 (spec requires 400, not Pydantic's 422)
    if len(payload.answer_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer must be at least 50 characters",
        )

    state = await _load_active_state(session_id)

    q_index: int = state.get("current_q_index", 0)
    if q_index >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already complete",
        )

    question = state["question_plan"][q_index]
    followup_count: int = state.get("current_followup_count", 0)

    # ── Arbiter decision (pure Python, synchronous) ──────────────────────────
    signals_with_hits = mark_signal_hits(question.get("expected_signals", []), payload.answer_text)
    decision = arbiter_decision(
        signals_with_hits,
        payload.answer_text,
        question.get("difficulty", "medium"),
        followup_count,
    )

    # ── FOLLOW-UP path ───────────────────────────────────────────────────────
    if decision["decision"] == "follow_up":
        new_followup_count = followup_count + 1
        state["current_followup_count"] = new_followup_count
        await set_session_state(session_id, state)

        return AnswerSubmitResponse(
            next_question=_to_question_response(question, new_followup_count),
            session_status="active",
            message=f"Follow-up: {decision['reason']}",
        )

    # ── PROCEED path ─────────────────────────────────────────────────────────
    # Fetch job once for both DB save and background task
    job = await db.get(Job, uuid.UUID(state["job_id"]))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Persist evaluation record (status=pending — evaluator will fill scores)
    eval_record = Evaluation(
        session_id=session_id,
        question_id=question["question_id"],
        question_text=question["question_text"],
        answer_text=payload.answer_text,
        followup_count=followup_count,
        eval_status="pending",
    )
    db.add(eval_record)
    await db.flush()
    await db.refresh(eval_record)
    eval_id = eval_record.id

    # Serialise job for background task (ORM session will be closed by then)
    job_data = {
        "title": job.title,
        "description": job.description or "",
        "required_skills": job.required_skills or [],
        "dimension_weights": job.dimension_weights or {},
    }

    # Launch GPT-4o evaluation as background task — response is returned immediately
    background_tasks.add_task(_evaluate_answer_bg, eval_id, question, payload.answer_text, job_data)

    # Advance state
    state["answers"].append(
        {"question_id": question["question_id"], "eval_id": str(eval_id)}
    )
    new_q_index = q_index + 1
    state["current_q_index"] = new_q_index
    state["current_followup_count"] = 0

    # ── Interview complete ───────────────────────────────────────────────────
    if new_q_index >= len(state["question_plan"]):
        state["status"] = "completed"
        await set_session_state(session_id, state)

        # Persist completed status to DB
        session_row = await db.get(InterviewSession, session_id)
        if session_row:
            session_row.status = "completed"
            await db.flush()

        return AnswerSubmitResponse(
            next_question=None,
            session_status="completed",
            message="Interview complete. Thank you for your responses!",
        )

    # ── Next question ────────────────────────────────────────────────────────
    await set_session_state(session_id, state)
    next_q = state["question_plan"][new_q_index]

    return AnswerSubmitResponse(
        next_question=_to_question_response(next_q, 0),
        session_status="active",
        message="Answer recorded. Here is your next question.",
    )


@router.get("/{session_id}/evaluation-status", response_model=EvaluationStatusResponse)
async def evaluation_status(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _recruiter: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> EvaluationStatusResponse:
    result = await db.execute(
        select(
            func.count(Evaluation.id).label("total"),
            func.count(Evaluation.id).filter(Evaluation.eval_status == "complete").label("evaluated"),
            func.count(Evaluation.id).filter(Evaluation.eval_status == "pending").label("pending"),
        ).where(Evaluation.session_id == session_id)
    )
    row = result.one()
    total: int = row.total or 0
    evaluated: int = row.evaluated or 0
    pending: int = row.pending or 0

    return EvaluationStatusResponse(
        total_answers=total,
        evaluated=evaluated,
        pending=pending,
        all_complete=(total > 0 and evaluated == total),
    )
