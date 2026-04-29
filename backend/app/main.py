import logging
import subprocess
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, interview, jobs, report, resumes, sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Run migrations before accepting traffic
    try:
        logger.info("Running database migrations...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/app",
        )
        if result.returncode != 0:
            logger.error(f"Migration failed (stdout): {result.stdout}")
            logger.error(f"Migration failed (stderr): {result.stderr}")
        else:
            logger.info(f"Migrations complete: {result.stdout.strip()}")
    except Exception as e:
        logger.error(f"Migration error: {e}")
        logger.error(traceback.format_exc())

    try:
        from app.core.database import engine  # noqa: F401
        logger.info("Startup: database engine initialized")
    except Exception as e:
        logger.error(f"STARTUP FAILED: {e}")
        logger.error(traceback.format_exc())
        raise
    yield
    try:
        from app.core.database import engine
        await engine.dispose()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


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
