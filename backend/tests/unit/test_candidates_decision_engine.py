"""
Decision Engine tests against three synthetic candidate profiles.

Verified score arithmetic (all weights default, normalised to 1.0):
  A: dims=9.8, resume=8.8 → interview=9.80, final=9.60, conf=0.733 → strong_hire
  B: dims≈8.3, -0.3 flag, resume=6.2 → interview=8.055, final=7.684, conf=0.456 → hire
  C: ps=4.2 (floor 4.5 violated), -0.8 flag, resume=5.5 → final=5.70, floor_override → reject
"""

from tests.fixtures.candidates import CANDIDATE_A, CANDIDATE_B, CANDIDATE_C
from app.engine.decision import DecisionEngine

STANDARD_JOB: dict = {"dimension_weights": {}}

engine = DecisionEngine()


def make_evaluations(
    scores: dict[str, float],
    hallucination_types: list[str] | tuple[str, ...] = (),
) -> list[dict]:
    """
    Build 6 evaluation dicts with identical dimension scores.
    hallucination_flags are plain strings (as the engine expects) on only the first eval.
    """
    evals = []
    for i in range(6):
        flags: list[str] = list(hallucination_types) if i == 0 else []
        evals.append(
            {
                "technical_accuracy": scores["technical_accuracy"],
                "depth_of_explanation": scores["depth_of_explanation"],
                "problem_solving": scores["problem_solving"],
                "communication_clarity": scores["communication_clarity"],
                "relevance": scores["relevance"],
                "reasoning_quality": scores["reasoning_quality"],
                "hallucination_flags": flags,
            }
        )
    return evals


def test_candidate_a_strong_hire() -> None:
    c = CANDIDATE_A
    evals = make_evaluations(c["dimension_scores"], c["hallucination_types"])
    report = engine.compute(evals, resume_score=c["resume_score"], job=STANDARD_JOB)

    assert report["tier"] == "strong_hire", f"Expected strong_hire, got {report['tier']}"
    assert report["final_score"] >= 9.5, f"Expected final_score >= 9.5, got {report['final_score']}"
    assert report["confidence"] >= 0.7, f"Expected confidence >= 0.7, got {report['confidence']}"
    assert report["floor_override"] is False
    assert report["floor_violations"] == []


def test_candidate_b_hire() -> None:
    c = CANDIDATE_B
    evals = make_evaluations(c["dimension_scores"], c["hallucination_types"])
    report = engine.compute(evals, resume_score=c["resume_score"], job=STANDARD_JOB)

    assert report["tier"] == "hire", f"Expected hire, got {report['tier']}"
    assert 7.0 <= report["final_score"] < 8.5, (
        f"Expected final_score in [7.0, 8.5), got {report['final_score']}"
    )
    assert report["confidence"] >= 0.4, f"Expected confidence >= 0.4, got {report['confidence']}"
    assert report["floor_override"] is False
    assert report["hallucination_penalty"] == -0.3


def test_candidate_c_floor_violation_reject() -> None:
    c = CANDIDATE_C
    evals = make_evaluations(c["dimension_scores"], c["hallucination_types"])
    report = engine.compute(evals, resume_score=c["resume_score"], job=STANDARD_JOB)

    assert report["tier"] == "reject", f"Expected reject, got {report['tier']}"
    assert report["floor_override"] is True
    assert "problem_solving" in report["floor_violations"]
    assert report["final_score"] >= 5.0, (
        f"Expected final_score >= 5.0 (floor override, not low score), got {report['final_score']}"
    )
    assert report["hallucination_penalty"] == -0.8
