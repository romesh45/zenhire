"""
Decision Engine — 100% deterministic Python. Zero LLM calls. Zero async.

Scoring pipeline:
  1. Validate minimum answer count
  2. Compute per-dimension averages across all evaluations
  3. Floor checks (hard thresholds per dimension)
  4. Hallucination penalty
  5. interview_score = weighted_sum − penalty
  6. final_score = interview×0.80 + resume×0.20
  7. Tier assignment
  8. Confidence computation
  9. Build and return report dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DIMENSION_KEYS: list[str] = [
    "technical_accuracy",
    "depth_of_explanation",
    "problem_solving",
    "communication_clarity",
    "relevance",
    "reasoning_quality",
]

FLOOR_THRESHOLDS: dict[str, float] = {
    "technical_accuracy": 5.0,
    "problem_solving": 4.5,
    "communication_clarity": 4.0,
    "depth_of_explanation": 4.0,
    "relevance": 3.5,
    "reasoning_quality": 3.5,
}

HALLUCINATION_PENALTIES: dict[str, float] = {
    "technical_falsehood": -0.8,
    "shallow_reasoning": -0.3,
    "experience_bluff": -0.5,
}
MAX_HALLUCINATION_PENALTY: float = -2.0
BLUFF_CARRY_THRESHOLD: int = 2
BLUFF_CARRY_PENALTY: float = -0.3

TIER_THRESHOLDS: list[tuple[float, str]] = [
    (8.5, "strong_hire"),
    (7.0, "hire"),
    (5.5, "maybe"),
    (0.0, "reject"),
]

CONFIDENCE_DENOMINATOR: float = 1.5
FLOOR_CONFIDENCE_MULTIPLIER: float = 0.7
BORDERLINE_DISTANCE: float = 0.1

DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "technical_accuracy": 0.25,
    "depth_of_explanation": 0.15,
    "problem_solving": 0.25,
    "communication_clarity": 0.15,
    "relevance": 0.10,
    "reasoning_quality": 0.10,
}


class DecisionEngine:
    def compute(
        self,
        evaluations: list[dict[str, Any]],
        resume_score: float,
        job: dict[str, Any],
    ) -> dict[str, Any]:
        # Step 1: Validate
        if len(evaluations) < 4:
            raise ValueError("incomplete_session")

        # Step 2: Per-dimension averages
        dimension_averages = self._compute_dimension_averages(evaluations)

        # Step 3: Floor checks
        floor_violations = self._check_floors(dimension_averages)
        floor_override = len(floor_violations) > 0

        # Step 4: Hallucination penalty
        penalty, bluff_answers = self._compute_hallucination_penalty(evaluations)

        # Step 5: interview_score = weighted sum − penalty
        weights = self._resolve_weights(job.get("dimension_weights") or {})
        weighted_sum = sum(
            dimension_averages[dim] * weights[dim] for dim in DIMENSION_KEYS
        )
        interview_score = max(0.0, min(10.0, weighted_sum + penalty))

        # Step 6: final_score
        has_resume = resume_score > 0.0
        if has_resume:
            final_score = interview_score * 0.80 + resume_score * 0.20
        else:
            final_score = interview_score * 1.0

        # Step 7: Tier
        tier = self._assign_tier(final_score, floor_override)

        # Step 8: Confidence
        confidence, borderline = self._compute_confidence(final_score, floor_override)

        # Step 9: Build report
        return {
            "tier": tier,
            "final_score": round(final_score, 4),
            "interview_score": round(interview_score, 4),
            "resume_score": round(resume_score, 4),
            "dimension_averages": {k: round(v, 4) for k, v in dimension_averages.items()},
            "floor_violations": floor_violations,
            "floor_override": floor_override,
            "hallucination_penalty": round(penalty, 4),
            "bluff_carry": bluff_answers >= BLUFF_CARRY_THRESHOLD,
            "confidence": round(confidence, 4),
            "borderline": borderline,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─── private helpers ──────────────────────────────────────────────────────

    def _compute_dimension_averages(self, evaluations: list[dict]) -> dict[str, float]:
        totals: dict[str, float] = {dim: 0.0 for dim in DIMENSION_KEYS}
        counts: dict[str, int] = {dim: 0 for dim in DIMENSION_KEYS}

        for ev in evaluations:
            for dim in DIMENSION_KEYS:
                val = ev.get(dim)
                if val is not None:
                    totals[dim] += float(val)
                    counts[dim] += 1

        return {
            dim: (totals[dim] / counts[dim] if counts[dim] > 0 else 0.0)
            for dim in DIMENSION_KEYS
        }

    def _check_floors(self, averages: dict[str, float]) -> list[str]:
        return [
            dim
            for dim, threshold in FLOOR_THRESHOLDS.items()
            if averages.get(dim, 0.0) < threshold
        ]

    def _compute_hallucination_penalty(
        self, evaluations: list[dict]
    ) -> tuple[float, int]:
        total_penalty = 0.0
        bluff_answers = 0

        for ev in evaluations:
            flags: list[str] = ev.get("hallucination_flags") or []
            answer_penalty = 0.0
            has_bluff = False
            for flag in flags:
                answer_penalty += HALLUCINATION_PENALTIES.get(flag, 0.0)
                if flag == "experience_bluff":
                    has_bluff = True
            total_penalty += answer_penalty
            if has_bluff:
                bluff_answers += 1

        # Cap
        total_penalty = max(total_penalty, MAX_HALLUCINATION_PENALTY)

        # Bluff carry penalty
        if bluff_answers >= BLUFF_CARRY_THRESHOLD:
            total_penalty += BLUFF_CARRY_PENALTY
            total_penalty = max(total_penalty, MAX_HALLUCINATION_PENALTY)

        return total_penalty, bluff_answers

    def _resolve_weights(self, raw_weights: dict[str, float]) -> dict[str, float]:
        weights = {**DEFAULT_DIMENSION_WEIGHTS, **{k: v for k, v in raw_weights.items() if k in DIMENSION_KEYS}}
        # Normalise so weights sum to 1.0
        total = sum(weights[dim] for dim in DIMENSION_KEYS)
        if total == 0.0:
            return DEFAULT_DIMENSION_WEIGHTS.copy()
        return {dim: weights[dim] / total for dim in DIMENSION_KEYS}

    def _assign_tier(self, final_score: float, floor_override: bool) -> str:
        if floor_override:
            return "reject"
        for threshold, tier in TIER_THRESHOLDS:
            if final_score >= threshold:
                return tier
        return "reject"

    def _compute_confidence(self, final_score: float, floor_override: bool) -> tuple[float, bool]:
        # Distance to nearest threshold boundary
        boundaries = [t for t, _ in TIER_THRESHOLDS]
        distances = [abs(final_score - b) for b in boundaries]
        min_distance = min(distances)

        confidence = min(1.0, min_distance / CONFIDENCE_DENOMINATOR)

        borderline = min_distance < BORDERLINE_DISTANCE

        if floor_override:
            confidence *= FLOOR_CONFIDENCE_MULTIPLIER

        return confidence, borderline
