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


# ─── Full orchestrated analysis ─────────────────────────────────────────────
#
# Single endpoint that runs every calculator (financial, eco, AHP, TOPSIS,
# sensitivity, comparison) for a stored project and returns the unified
# blob the frontend / report-service consumes. Implements TS §2 item 7
# ("simultaneous application of all methods") on the server side.


_FUEL_TYPES = ("natural_gas", "electricity", "coal", "diesel", "heating_oil")


class FullAnalysisRequest(BaseModel):
    discount_rate: float = Field(default=0.1, gt=-1.0, le=10.0)
    fuel_type: str = Field(default="electricity")
    co2_price_per_ton: float = Field(default=30.0, ge=0.0)
    damage_coefficient: float = Field(default=100.0, ge=0.0)
    sensitivity_variation_percent: float = Field(default=20.0, gt=0.0, le=100.0)

    @field_validator("fuel_type")
    @classmethod
    def _validate_fuel(cls, v: str) -> str:
        if v not in _FUEL_TYPES:
            raise ValueError(f"fuel_type must be one of: {_FUEL_TYPES}")
        return v


class FullAnalysisResponse(BaseModel):
    project_id: int
    project_name: str
    discount_rate: float
    financial: dict
    eco: dict
    ahp: Optional[dict] = None
    topsis: Optional[dict] = None
    comparison: dict
    sensitivity: Optional[dict] = None
