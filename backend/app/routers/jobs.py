from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_recruiter
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.schemas.job import JobCreate, JobResponse

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    recruiter: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> Job:
    try:
        job = Job(
            title=payload.title,
            description=payload.description,
            required_skills=payload.required_skills,
            dimension_weights=payload.dimension_weights.model_dump(),
            created_by_recruiter_id=recruiter.id,
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        return job
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job",
        ) from exc


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Recruiter, Depends(get_current_recruiter)],
) -> list[Job]:
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    return list(result.scalars().all())
