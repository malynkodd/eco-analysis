from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class BaseScenario(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    initial_investment: float = Field(ge=0)
    operational_cost: float = Field(ge=0)
    expected_savings: float = Field(ge=0)
    lifetime_years: int = Field(ge=1, le=100)
    discount_rate: float = Field(default=0.1, gt=-1.0, le=10.0)


# ─── What-if ────────────────────────────────────────────────


_WHATIF_PARAMS = {
    "initial_investment",
    "operational_cost",
    "expected_savings",
    "lifetime_years",
    "discount_rate",
}


class WhatIfParameter(BaseModel):
    parameter: str
    new_value: float

    @field_validator("parameter")
    @classmethod
    def _known_parameter(cls, v: str) -> str:
        if v not in _WHATIF_PARAMS:
            raise ValueError(f"Unknown parameter '{v}'")
        return v


class WhatIfInput(BaseModel):
    base: BaseScenario
    changes: List[WhatIfParameter] = Field(min_length=1)


class WhatIfResult(BaseModel):
    name: str
    parameter_changed: str
    original_value: float
    new_value: float
    original_npv: float
    new_npv: float
    npv_change: float
    npv_change_percent: float


# ─── Sensitivity ────────────────────────────────────────────


class SensitivityInput(BaseModel):
    base: BaseScenario
    variation_percent: float = Field(default=20.0, gt=0.0, le=100.0)
    steps: int = Field(default=5, ge=1, le=50)


class SensitivityPoint(BaseModel):
    variation_percent: float
    value: float
    npv: float


class SensitivityResult(BaseModel):
    parameter: str
    base_value: float
    base_npv: float
    impact_absolute: float
    impact_percent: float
    points: List[SensitivityPoint]


class SensitivityAnalysisResult(BaseModel):
    base_npv: float
    results: List[SensitivityResult]


# ─── Break-even ─────────────────────────────────────────────


class BreakEvenInput(BaseModel):
    base: BaseScenario


class BreakEvenResult(BaseModel):
    base_npv: float
    breakeven_savings: Optional[float] = None
    breakeven_investment: Optional[float] = None
    breakeven_discount_rate: Optional[float] = None
    breakeven_years: Optional[float] = None
