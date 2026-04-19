"""Pydantic v2 schemas for the project service."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeasureType(str, Enum):
    insulation = "insulation"
    equipment = "equipment"
    treatment = "treatment"
    renewable = "renewable"


# ─── Measure ─────────────────────────────────────────────────────────────────


class MeasureCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    measure_type: MeasureType
    initial_investment: float = Field(ge=0)
    operational_cost: float = Field(ge=0)
    expected_savings: float = Field(ge=0)
    lifetime_years: int = Field(ge=1, le=100)
    emission_reduction: float = Field(ge=0)


class MeasureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    measure_type: MeasureType
    initial_investment: float
    operational_cost: float
    expected_savings: float
    lifetime_years: int
    emission_reduction: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── Project ─────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10_000)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    owner_id: int
    status: str = "pending"
    manager_comment: Optional[str] = None
    measures: List[MeasureResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── Status changes ──────────────────────────────────────────────────────────

_ALLOWED_STATUSES = ("approved", "rejected", "pending")


class StatusUpdate(BaseModel):
    status: str
    manager_comment: Optional[str] = Field(default=None, max_length=10_000)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in _ALLOWED_STATUSES:
            raise ValueError(f"status must be one of: {_ALLOWED_STATUSES}")
        return v
