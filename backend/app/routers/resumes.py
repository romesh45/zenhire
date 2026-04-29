import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.resume import Resume
from app.models.session import Session as InterviewSession
from app.schemas.resume import ResumeUploadResponse

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    session_id: uuid.UUID = Form(...),
    resume_pdf: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    # Validate session
    session = await db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is '{session.status}'; resume upload only allowed for pending sessions",
        )

    # Validate file type
    filename = resume_pdf.filename or ""
    content_type = resume_pdf.content_type or ""
    if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    # Read and size-check
    pdf_bytes = await resume_pdf.read()
    if len(pdf_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {len(pdf_bytes) / 1024 / 1024:.1f} MB (max 5 MB)",
        )
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded")

    resume = Resume(
        session_id=session_id,
        filename=filename or "resume.pdf",
        pdf_data=pdf_bytes,
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)

    return ResumeUploadResponse(
        resume_id=resume.id,
        filename=resume.filename,
        session_id=session_id,
    )
