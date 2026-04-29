import json
import logging

from app.services.ai_router import llm_smart

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are an expert technical recruiter evaluating resumes."

_REQUIRED_FIELDS = {
    "skills_found": list,
    "experience_years": (int, float),
    "education": str,
    "projects": list,
    "skill_gaps": list,
    "strengths": list,
    "resume_score": (int, float),
    "confidence": (int, float),
    "reasoning": str,
}

_DEFAULTS: dict = {
    "skills_found": [],
    "experience_years": 0,
    "education": "Not specified",
    "projects": [],
    "skill_gaps": [],
    "strengths": [],
    "resume_score": 5.0,
    "confidence": 0.5,
    "reasoning": "Analysis incomplete.",
}


def _safe_float(value: object, lo: float, hi: float, default: float) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return default


async def run_resume_agent(pdf_text: str, job: object) -> dict:
    required_skills = getattr(job, "required_skills", []) or []
    job_title = getattr(job, "title", "")
    job_description = getattr(job, "description", "") or ""

    user_prompt = f"""Analyse the resume below for the role of **{job_title}**.

Job description:
{job_description}

Required skills: {", ".join(required_skills)}

Resume:
{pdf_text}

Return a JSON object with exactly these keys:
- skills_found: array of strings — skills identified in the resume
- experience_years: integer — total years of professional experience
- education: string — highest qualification
- projects: array of strings — notable projects or achievements (brief descriptions)
- skill_gaps: array of strings — required skills missing from the resume
- strengths: array of strings — candidate's top strengths relevant to this role
- resume_score: float 0–10 — composite quality score
- confidence: float 0–1 — your confidence in this assessment
- reasoning: string — one paragraph justifying the resume_score

Return ONLY the JSON object. No markdown, no explanation, no code blocks."""

    try:
        raw = await llm_smart(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        result: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Resume agent returned invalid JSON: %s", exc)
        raise ValueError(f"Resume agent returned invalid JSON: {exc}") from exc
    except Exception as exc:
        logger.error("Resume agent LLM call failed: %s", exc)
        raise

    for field, expected_type in _REQUIRED_FIELDS.items():
        if field not in result or not isinstance(result[field], expected_type):
            result[field] = _DEFAULTS[field]

    result["resume_score"] = _safe_float(result["resume_score"], 0.0, 10.0, 5.0)
    result["confidence"] = _safe_float(result["confidence"], 0.0, 1.0, 0.5)

    return result
