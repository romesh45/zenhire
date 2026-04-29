import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator


class DimensionWeights(BaseModel):
    technical_accuracy: float
    depth_of_explanation: float
    problem_solving: float
    communication_clarity: float
    relevance: float
    reasoning_quality: float

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> "DimensionWeights":
        total = (
            self.technical_accuracy
            + self.depth_of_explanation
            + self.problem_solving
            + self.communication_clarity
            + self.relevance
            + self.reasoning_quality
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"dimension_weights must sum to 1.0, got {total:.6f}")
        return self


class JobCreate(BaseModel):
    title: str
    description: str | None = None
    required_skills: list[str] = []
    dimension_weights: DimensionWeights


class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    required_skills: list[str]
    dimension_weights: DimensionWeights
    created_by_recruiter_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
