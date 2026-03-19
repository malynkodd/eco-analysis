from pydantic import BaseModel
from typing import List, Dict


class BaseScenario(BaseModel):
    """Базові параметри заходу для сценарного моделювання"""
    name: str
    initial_investment: float
    operational_cost: float
    expected_savings: float
    lifetime_years: int
    discount_rate: float = 0.1


# ─── What-if аналіз ───────────────────────────────────

class WhatIfParameter(BaseModel):
    parameter: str        # назва параметру
    new_value: float      # нове значення


class WhatIfInput(BaseModel):
    base: BaseScenario
    changes: List[WhatIfParameter]


class WhatIfResult(BaseModel):
    name: str
    parameter_changed: str
    original_value: float
    new_value: float
    original_npv: float
    new_npv: float
    npv_change: float
    npv_change_percent: float


# ─── Sensitivity Analysis ─────────────────────────────

class SensitivityInput(BaseModel):
    base: BaseScenario
    variation_percent: float = 20.0   # варіація ±20%
    steps: int = 5                    # кількість кроків


class SensitivityPoint(BaseModel):
    variation_percent: float
    value: float
    npv: float


class SensitivityResult(BaseModel):
    parameter: str
    base_value: float
    base_npv: float
    impact_percent: float             # вплив на NPV (для tornado chart)
    points: List[SensitivityPoint]


class SensitivityAnalysisResult(BaseModel):
    base_npv: float
    results: List[SensitivityResult]  # відсортовано за впливом (tornado)


# ─── Break-even аналіз ────────────────────────────────

class BreakEvenInput(BaseModel):
    base: BaseScenario


class BreakEvenResult(BaseModel):
    base_npv: float
    breakeven_savings: float          # мін. економія при NPV=0
    breakeven_investment: float       # макс. інвестиція при NPV=0
    breakeven_discount_rate: float    # макс. ставка при NPV=0
    breakeven_years: float            # мін. термін при NPV=0