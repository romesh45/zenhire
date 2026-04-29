from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.recruiter import Recruiter
from app.schemas.auth import LoginRequest, RecruiterCreate, RecruiterResponse, TokenResponse

router = APIRouter()


@router.post("/register", response_model=RecruiterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RecruiterCreate, db: AsyncSession = Depends(get_db)) -> Recruiter:
    existing = await db.execute(
        select(Recruiter).where(Recruiter.email == payload.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    recruiter = Recruiter(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(recruiter)
    await db.flush()
    await db.refresh(recruiter)
    return recruiter


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(Recruiter).where(Recruiter.email == payload.email))
    recruiter = result.scalar_one_or_none()

    if recruiter is None or not verify_password(payload.password, recruiter.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(recruiter.id)})
    return TokenResponse(access_token=token)
