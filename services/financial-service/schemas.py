from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class FinancialInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    initial_investment: float = Field(ge=0)
    operational_cost: float = Field(ge=0)
    expected_savings: float = Field(ge=0)
    lifetime_years: int = Field(ge=1, le=100)
    discount_rate: float = Field(default=0.1, gt=-1.0, le=10.0)


class IRRResult(BaseModel):
    value: Optional[float] = Field(
        default=None,
        description="IRR in percent. None when no real root exists in [-99%, +1000%].",
    )
    converged: bool = False
    iterations: int = 0


class YearlyDetail(BaseModel):
    year: int = Field(ge=1)
    cash_flow: float
    discounted_cash_flow: float
    cumulative_cash_flow: float
    cumulative_discounted: float


class FinancialResult(BaseModel):
    name: str
    npv: float
    irr: IRRResult
    bcr: Optional[float] = None
    simple_payback: Optional[float] = None
    discounted_payback: Optional[float] = None
    lcca: float
    yearly_details: List[YearlyDetail]


class PortfolioInput(BaseModel):
    measures: List[FinancialInput] = Field(min_length=1)
    discount_rate: float = Field(default=0.1, gt=-1.0, le=10.0)

    @field_validator("measures")
    @classmethod
    def _unique_names(cls, v: List[FinancialInput]) -> List[FinancialInput]:
        names = [m.name for m in v]
        if len(set(names)) != len(names):
            raise ValueError("Measure names must be unique within a portfolio")
        return v


class PortfolioResult(BaseModel):
    results: List[FinancialResult]
