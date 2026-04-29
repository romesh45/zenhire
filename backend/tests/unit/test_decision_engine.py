import pytest

from app.engine.decision import DecisionEngine

ENGINE = DecisionEngine()

JOB = {
    "title": "Senior Python Engineer",
    "dimension_weights": {
        "technical_accuracy": 0.25,
        "depth_of_explanation": 0.15,
        "problem_solving": 0.25,
        "communication_clarity": 0.15,
        "relevance": 0.10,
        "reasoning_quality": 0.10,
    },
}


def _make_eval(
    *,
    technical_accuracy: float = 8.0,
    depth_of_explanation: float = 7.5,
    problem_solving: float = 8.0,
    communication_clarity: float = 7.0,
    relevance: float = 8.0,
    reasoning_quality: float = 7.5,
    hallucination_flags: list | None = None,
) -> dict:
    return {
        "technical_accuracy": technical_accuracy,
        "depth_of_explanation": depth_of_explanation,
        "problem_solving": problem_solving,
        "communication_clarity": communication_clarity,
        "relevance": relevance,
        "reasoning_quality": reasoning_quality,
        "hallucination_flags": hallucination_flags or [],
    }


def _six_clean_evals(**overrides) -> list[dict]:
    return [_make_eval(**overrides) for _ in range(6)]


class TestStrongHire:
    def test_strong_hire_clean(self):
        evals = _six_clean_evals(
            technical_accuracy=9.5,
            depth_of_explanation=9.0,
            problem_solving=9.2,
            communication_clarity=9.0,
            relevance=9.3,
            reasoning_quality=9.1,
        )
        report = ENGINE.compute(evals, resume_score=8.5, job=JOB)

        assert report["tier"] == "strong_hire"
        assert report["final_score"] >= 8.5
        assert report["floor_override"] is False
        assert report["hallucination_penalty"] == 0.0
        assert report["bluff_carry"] is False
        assert 0.0 <= report["confidence"] <= 1.0


class TestHireModerate:
    def test_hire_moderate(self):
        # Weights: tech=0.25, depth=0.15, ps=0.25, comm=0.15, rel=0.10, rq=0.10
        # weighted_sum ≈ 7.345 → interview_score=7.345 → final=7.345×0.80+6.0×0.20=7.076
        evals = _six_clean_evals(
            technical_accuracy=7.8,
            depth_of_explanation=7.0,
            problem_solving=7.5,
            communication_clarity=7.0,
            relevance=7.2,
            reasoning_quality=7.0,
        )
        report = ENGINE.compute(evals, resume_score=6.0, job=JOB)

        assert report["tier"] == "hire"
        assert 7.0 <= report["final_score"] < 8.5
        assert report["floor_override"] is False


class TestFloorViolationOverride:
    def test_floor_violation_forces_reject(self):
        # technical_accuracy below floor (5.0) → reject regardless of final_score
        evals = _six_clean_evals(
            technical_accuracy=3.0,  # below 5.0 floor
            depth_of_explanation=9.0,
            problem_solving=9.0,
            communication_clarity=9.0,
            relevance=9.0,
            reasoning_quality=9.0,
        )
        report = ENGINE.compute(evals, resume_score=9.0, job=JOB)

        assert report["tier"] == "reject"
        assert report["floor_override"] is True
        assert "technical_accuracy" in report["floor_violations"]
        # Confidence should be reduced
        assert report["confidence"] <= 0.7


class TestHallucinationPenalty:
    def test_technical_falsehood_penalty(self):
        # Baseline without flags
        clean_evals = _six_clean_evals(
            technical_accuracy=8.0,
            depth_of_explanation=7.5,
            problem_solving=8.0,
            communication_clarity=7.5,
            relevance=8.0,
            reasoning_quality=7.5,
        )
        clean_report = ENGINE.compute(clean_evals, resume_score=7.0, job=JOB)

        # Same scores but first eval has technical_falsehood flag
        flagged_evals = [
            _make_eval(
                technical_accuracy=8.0,
                depth_of_explanation=7.5,
                problem_solving=8.0,
                communication_clarity=7.5,
                relevance=8.0,
                reasoning_quality=7.5,
                hallucination_flags=["technical_falsehood"],
            )
        ] + _six_clean_evals(
            technical_accuracy=8.0,
            depth_of_explanation=7.5,
            problem_solving=8.0,
            communication_clarity=7.5,
            relevance=8.0,
            reasoning_quality=7.5,
        )
        flagged_report = ENGINE.compute(flagged_evals, resume_score=7.0, job=JOB)

        assert flagged_report["hallucination_penalty"] < 0.0
        assert flagged_report["final_score"] < clean_report["final_score"]


class TestIncompleteSession:
    def test_incomplete_session_raises(self):
        evals = [_make_eval() for _ in range(3)]  # fewer than 4

        with pytest.raises(ValueError, match="incomplete_session"):
            ENGINE.compute(evals, resume_score=7.0, job=JOB)
