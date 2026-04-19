from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AHPInput(BaseModel):
    criteria: List[str] = Field(min_length=2, max_length=10)
    comparison_matrix: List[List[float]]
    alternatives: List[dict] = Field(min_length=1)
    is_benefit: Optional[List[bool]] = None

    @field_validator("comparison_matrix")
    @classmethod
    def _matrix_non_empty(cls, v: List[List[float]]) -> List[List[float]]:
        if not v or any(len(row) != len(v) for row in v):
            raise ValueError("Comparison matrix must be a non-empty square matrix")
        return v


class AHPResult(BaseModel):
    criteria: List[str]
    weights: List[float]
    consistency_ratio: float
    is_consistent: bool
    lambda_max: float
    ranking: List[dict]


class TOPSISInput(BaseModel):
    criteria: List[str] = Field(min_length=1)
    weights: List[float] = Field(min_length=1)
    is_benefit: List[bool] = Field(min_length=1)
    alternatives: List[dict] = Field(min_length=1)


class TOPSISResult(BaseModel):
    criteria: List[str]
    weights: List[float]
    ranking: List[dict]


class CombinedInput(BaseModel):
    criteria: List[str] = Field(min_length=2, max_length=10)
    comparison_matrix: List[List[float]]
    is_benefit: List[bool] = Field(min_length=2, max_length=10)
    alternatives: List[dict] = Field(min_length=1)


class CombinedResult(BaseModel):
    ahp: AHPResult
    topsis: TOPSISResult
