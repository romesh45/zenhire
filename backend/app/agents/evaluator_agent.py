import json
import logging

from app.services.ai_router import llm_smart

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are an expert technical evaluator. Score this interview answer."

_DIMENSIONS = [
    "technical_accuracy",
    "depth_of_explanation",
    "problem_solving",
    "communication_clarity",
    "relevance",
    "reasoning_quality",
]
_VALID_HALLUCINATION_TYPES = {
    "technical_falsehood",
    "shallow_reasoning",
    "experience_bluff",
}


def _clamp(value: object, default: float = 5.0) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
        return max(0.0, min(10.0, v))
    except (TypeError, ValueError):
        return default


async def run_evaluator_agent(question: dict, answer_text: str, job: object) -> dict:
    job_title = getattr(job, "title", "") if not isinstance(job, dict) else job.get("title", "")
    dimension_weights = (
        getattr(job, "dimension_weights", {})
        if not isinstance(job, dict)
        else job.get("dimension_weights", {})
    )

    signals_text = "\n".join(
        f"  - {s['name']} (importance: {s['importance']})"
        for s in question.get("expected_signals", [])
    )

    user_prompt = f"""Role being interviewed for: {job_title}

Question asked:
\"{question.get('question_text', '')}\"

Expected signals (what the ideal answer should cover):
{signals_text or '  (none specified)'}

Candidate's answer:
\"{answer_text}\"

Score the answer on each dimension (0–10 float, where 10 is expert-level):
- technical_accuracy: correctness of technical claims
- depth_of_explanation: thoroughness of explanation
- problem_solving: structured approach to the problem
- communication_clarity: how clearly the answer is communicated
- relevance: how well the answer addresses what was asked
- reasoning_quality: quality of logical reasoning and justification

Also identify any hallucination flags (can be empty list):
- technical_falsehood: factually incorrect claim
- shallow_reasoning: plausible-sounding but lacks substance
- experience_bluff: claims experience that contradicts answer quality

Return a JSON object with exactly:
{{
  "technical_accuracy": <float 0-10>,
  "depth_of_explanation": <float 0-10>,
  "problem_solving": <float 0-10>,
  "communication_clarity": <float 0-10>,
  "relevance": <float 0-10>,
  "reasoning_quality": <float 0-10>,
  "hallucination_flags": [
    {{"type": "<type>", "detail": "<one sentence description>"}}
  ],
  "audit_trace": "<2-4 sentence detailed evaluation reasoning>",
  "recruiter_summary": "<one plain-English sentence for the recruiter>"
}}

Dimension weights for context: {json.dumps(dimension_weights)}
Return ONLY the JSON object. No markdown. No explanation."""

    raw = await llm_smart(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Evaluator agent returned invalid JSON: %s", exc)
        raise ValueError(f"Evaluator agent returned invalid JSON: {exc}") from exc

    for dim in _DIMENSIONS:
        result[dim] = _clamp(result.get(dim), default=5.0)

    raw_flags = result.get("hallucination_flags")
    if not isinstance(raw_flags, list):
        result["hallucination_flags"] = []
    else:
        result["hallucination_flags"] = [
            {"type": f.get("type", ""), "detail": f.get("detail", "")}
            for f in raw_flags
            if isinstance(f, dict) and f.get("type") in _VALID_HALLUCINATION_TYPES
        ]

    if not isinstance(result.get("audit_trace"), str):
        result["audit_trace"] = "Evaluation completed."
    if not isinstance(result.get("recruiter_summary"), str):
        result["recruiter_summary"] = "Answer evaluated."

    return result
