from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine
from app.routers import auth, interview, jobs, report, resumes, sessions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


app = FastAPI(title="Zenhire API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(interview.router, prefix="/sessions", tags=["interview"])
app.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
app.include_router(report.router, prefix="/sessions", tags=["report"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "zenhire-api"}


@app.get("/health/providers")
async def health_providers() -> dict[str, object]:
    from app.core.config import settings

    return {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "openrouter": bool(settings.OPENROUTER_API_KEY),
        "embeddings_available": True,  # sentence-transformers, always local
        "active_providers": settings.active_providers,
        "active_count": len(settings.active_providers),
    }
