import json
import logging

from app.services.ai_router import llm_fast

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a senior technical interviewer. Generate targeted interview questions."

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_VALID_IMPORTANCES = {"critical", "optional"}


def _valid_signal(s: object) -> bool:
    if not isinstance(s, dict):
        return False
    return (
        isinstance(s.get("name"), str)
        and s.get("importance") in _VALID_IMPORTANCES
    )


def _validate_question(q: object, idx: int) -> dict | None:
    if not isinstance(q, dict):
        return None

    question_id = f"q{idx + 1}"
    question_text = q.get("question_text") or q.get("question", "")
    difficulty = q.get("difficulty", "medium")
    raw_signals = q.get("expected_signals") or []

    if not isinstance(question_text, str) or len(question_text.strip()) < 10:
        return None
    if difficulty not in _VALID_DIFFICULTIES:
        difficulty = "medium"

    signals = [s for s in raw_signals if _valid_signal(s)]
    if not signals:
        return None
    if not any(s.get("importance") == "critical" for s in signals):
        signals[0] = {**signals[0], "importance": "critical"}

    return {
        "question_id": question_id,
        "question_text": question_text.strip(),
        "difficulty": difficulty,
        "expected_signals": signals,
    }


async def run_interview_agent(job: object, resume_structured: dict) -> list[dict]:
    job_title = getattr(job, "title", "")
    required_skills = getattr(job, "required_skills", []) or []
    job_description = getattr(job, "description", "") or ""
    skill_gaps = resume_structured.get("skill_gaps", [])
    strengths = resume_structured.get("strengths", [])

    user_prompt = f"""Generate exactly 6 interview questions for the role: **{job_title}**

Job description: {job_description}
Required skills: {", ".join(required_skills)}
Candidate's skill gaps: {", ".join(skill_gaps) or "none identified"}
Candidate's strengths: {", ".join(strengths) or "none identified"}

Return a JSON object with a single key "questions" whose value is an array of 6 objects.
Each object must have:
- question_id: "q1" through "q6"
- question_text: the interview question (be specific and technical)
- difficulty: one of "easy", "medium", "hard"
- expected_signals: array of 2-4 objects, each with:
    - name: snake_case signal name (e.g. "explains_event_loop")
    - importance: "critical" or "optional"
  At least one signal must be "critical".

Focus on skill gaps first, then required skills. Mix difficulties: 1 easy, 3 medium, 2 hard.
Return ONLY the JSON object. No markdown. No explanation."""

    raw = await llm_fast(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Interview agent returned invalid JSON: %s", exc)
        raise ValueError(f"Interview agent returned invalid JSON: {exc}") from exc

    raw_questions = data.get("questions") or []
    validated: list[dict] = []
    for i, q in enumerate(raw_questions[:6]):
        clean = _validate_question(q, i)
        if clean:
            validated.append(clean)

    if len(validated) < 4:
        raise ValueError(
            f"Interview agent returned only {len(validated)} valid questions (need >= 4)"
        )

    for i, q in enumerate(validated):
        q["question_id"] = f"q{i + 1}"

    return validated
