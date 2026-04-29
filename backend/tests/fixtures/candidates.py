"""
Synthetic candidate fixtures for Decision Engine unit tests.

Three calibrated profiles:
  CANDIDATE_A — strong hire (all dimensions near-perfect)
  CANDIDATE_B — hire (solid performer, one minor flag, lower resume score)
  CANDIDATE_C — floor violation reject (problem_solving below hard floor)
"""

CANDIDATE_A = {
    "name": "Alice Chen",
    "role": "Senior Backend Engineer",
    "resume_score": 8.8,
    "dimension_scores": {
        "technical_accuracy": 9.8,
        "depth_of_explanation": 9.8,
        "problem_solving": 9.8,
        "communication_clarity": 9.8,
        "relevance": 9.8,
        "reasoning_quality": 9.8,
    },
    "hallucination_types": [],
    "expected_tier": "strong_hire",
    "notes": "All dimensions near-perfect; final_score ~9.60 → confidence ~0.73",
}

CANDIDATE_B = {
    "name": "Ben Patel",
    "role": "Mid-level Backend Engineer",
    "resume_score": 6.2,
    "dimension_scores": {
        "technical_accuracy": 8.7,
        "depth_of_explanation": 8.2,
        "problem_solving": 8.4,
        "communication_clarity": 8.2,
        "relevance": 8.2,
        "reasoning_quality": 8.0,
    },
    "hallucination_types": ["shallow_reasoning"],
    "expected_tier": "hire",
    "notes": "Solid scores with one shallow_reasoning flag; final_score ~7.68 → confidence ~0.46",
}

CANDIDATE_C = {
    "name": "Carlos Mendez",
    "role": "Junior Backend Engineer",
    "resume_score": 5.5,
    "dimension_scores": {
        "technical_accuracy": 8.0,
        "depth_of_explanation": 7.0,
        "problem_solving": 4.2,
        "communication_clarity": 7.0,
        "relevance": 7.0,
        "reasoning_quality": 7.0,
    },
    "hallucination_types": ["technical_falsehood"],
    "expected_tier": "reject",
    "notes": "problem_solving=4.2 violates floor of 4.5 → forced reject regardless of weighted score",
}

ALL_CANDIDATES = [CANDIDATE_A, CANDIDATE_B, CANDIDATE_C]
