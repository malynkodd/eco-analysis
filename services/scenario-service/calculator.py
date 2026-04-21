"""Scenario engine — what-if, sensitivity (tornado), break-even.

NPV is computed in closed form. Break-even points are solved with
``scipy.optimize.brentq`` over explicit, sane brackets — when the base
parameter is zero we substitute a default upper bound so bisection still
brackets the root. Sensitivity reports both an absolute NPV swing
(``impact_absolute``, currency units) and a relative swing
(``impact_percent``, percent of |base NPV|).
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
from schemas import (
    BaseScenario,
    BreakEvenInput,
    BreakEvenResult,
    SensitivityAnalysisResult,
    SensitivityInput,
    SensitivityPoint,
    SensitivityResult,
    WhatIfInput,
    WhatIfResult,
)
from scipy.optimize import brentq

logger = logging.getLogger(__name__)

# Fallback upper bounds (used when the base value is 0 so we still bracket).
_FALLBACK_UPPER = {
    "initial_investment": 1_000_000.0,
    "operational_cost": 100_000.0,
    "expected_savings": 100_000.0,
    "discount_rate": 9.99,
    "lifetime_years": 100,
}


def calc_npv(
    initial_investment: float,
    operational_cost: float,
    expected_savings: float,
    lifetime_years: int,
    discount_rate: float,
) -> float:
    if discount_rate <= -1.0:
        raise ValueError("discount_rate must be > -1")
    if lifetime_years < 1:
        raise ValueError("lifetime_years must be >= 1")
    annual_cf = expected_savings - operational_cost
    factor = 1.0 + discount_rate
    npv = -initial_investment + sum(annual_cf / (factor**t) for t in range(1, lifetime_years + 1))
    return round(npv, 2)


def run_whatif(data: WhatIfInput) -> List[WhatIfResult]:
    b = data.base
    base_npv = calc_npv(
        b.initial_investment,
        b.operational_cost,
        b.expected_savings,
        b.lifetime_years,
        b.discount_rate,
    )

    results: List[WhatIfResult] = []
    for change in data.changes:
        params = {
            "initial_investment": b.initial_investment,
            "operational_cost": b.operational_cost,
            "expected_savings": b.expected_savings,
            "lifetime_years": b.lifetime_years,
            "discount_rate": b.discount_rate,
        }
        if change.parameter not in params:
            raise ValueError(f"Unknown parameter '{change.parameter}'")
        original_value = params[change.parameter]
        params[change.parameter] = change.new_value
        new_npv = calc_npv(**params)
        npv_change = new_npv - base_npv
        npv_change_pct = (npv_change / abs(base_npv) * 100) if base_npv != 0 else 0.0

        results.append(
            WhatIfResult(
                name=b.name,
                parameter_changed=change.parameter,
                original_value=float(original_value),
                new_value=float(change.new_value),
                original_npv=base_npv,
                new_npv=new_npv,
                npv_change=round(npv_change, 2),
                npv_change_percent=round(npv_change_pct, 2),
            )
        )
    return results


def run_sensitivity(data: SensitivityInput) -> SensitivityAnalysisResult:
    b = data.base
    base_npv = calc_npv(
        b.initial_investment,
        b.operational_cost,
        b.expected_savings,
        b.lifetime_years,
        b.discount_rate,
    )

    parameters = {
        "expected_savings": b.expected_savings,
        "initial_investment": b.initial_investment,
        "discount_rate": b.discount_rate,
        "operational_cost": b.operational_cost,
        "lifetime_years": float(b.lifetime_years),
    }

    sensitivity_results: List[SensitivityResult] = []
    v = data.variation_percent / 100.0

    for param_name, base_value in parameters.items():
        npv_values: List[float] = []
        points: List[SensitivityPoint] = []
        variations = np.linspace(-v, v, data.steps * 2 + 1)

        for var in variations:
            params = {
                "initial_investment": b.initial_investment,
                "operational_cost": b.operational_cost,
                "expected_savings": b.expected_savings,
                "lifetime_years": b.lifetime_years,
                "discount_rate": b.discount_rate,
            }
            if base_value == 0:
                abs_step = {
                    "initial_investment": 10_000,
                    "operational_cost": 1_000,
                    "expected_savings": 1_000,
                    "discount_rate": 0.01,
                    "lifetime_years": 1,
                }[param_name]
                new_value = abs_step * var
            else:
                new_value = base_value * (1 + var)

            if param_name == "lifetime_years":
                params[param_name] = max(1, int(round(new_value)))
            elif param_name == "discount_rate":
                params[param_name] = max(0.001, new_value)
            else:
                params[param_name] = max(0.0, new_value)

            npv = calc_npv(**params)
            npv_values.append(npv)
            points.append(
                SensitivityPoint(
                    variation_percent=round(var * 100, 2),
                    value=round(float(new_value), 4),
                    npv=npv,
                )
            )

        impact_abs = max(npv_values) - min(npv_values)
        impact_pct = (impact_abs / abs(base_npv) * 100) if base_npv != 0 else 0.0
        sensitivity_results.append(
            SensitivityResult(
                parameter=param_name,
                base_value=float(base_value),
                base_npv=base_npv,
                impact_absolute=round(impact_abs, 2),
                impact_percent=round(impact_pct, 2),
                points=points,
            )
        )

    sensitivity_results.sort(key=lambda x: x.impact_absolute, reverse=True)
    logger.info(
        "Sensitivity for '%s': base_npv=%.2f, top='%s'",
        b.name,
        base_npv,
        sensitivity_results[0].parameter if sensitivity_results else "n/a",
    )

    return SensitivityAnalysisResult(base_npv=base_npv, results=sensitivity_results)


def _solve_breakeven(
    param_name: str, lower: float, upper: float, base: BaseScenario
) -> Optional[float]:
    """Return the value of *param_name* at which NPV crosses 0 within (lower, upper)."""

    def f(val: float) -> float:
        params = {
            "initial_investment": base.initial_investment,
            "operational_cost": base.operational_cost,
            "expected_savings": base.expected_savings,
            "lifetime_years": base.lifetime_years,
            "discount_rate": base.discount_rate,
        }
        params[param_name] = max(1, int(round(val))) if param_name == "lifetime_years" else val
        return calc_npv(**params)

    try:
        f_low, f_high = f(lower), f(upper)
    except ValueError:
        return None
    if f_low * f_high > 0:
        logger.debug(
            "Break-even for '%s' not bracketed in [%s, %s]: f(low)=%s, f(high)=%s",
            param_name,
            lower,
            upper,
            f_low,
            f_high,
        )
        return None
    try:
        root = brentq(f, lower, upper, xtol=1e-4, maxiter=200)
        return float(root)
    except (RuntimeError, ValueError) as exc:
        logger.warning("Break-even brentq failed for '%s': %s", param_name, exc)
        return None


def _bracket_upper(param_name: str, base_value: float, multiplier: float = 10.0) -> float:
    if base_value > 0:
        return base_value * multiplier
    return _FALLBACK_UPPER[param_name]


def run_breakeven(data: BreakEvenInput) -> BreakEvenResult:
    b = data.base
    base_npv = calc_npv(
        b.initial_investment,
        b.operational_cost,
        b.expected_savings,
        b.lifetime_years,
        b.discount_rate,
    )

    breakeven_savings = _solve_breakeven(
        "expected_savings",
        0.0,
        _bracket_upper("expected_savings", b.expected_savings),
        b,
    )
    breakeven_investment = _solve_breakeven(
        "initial_investment",
        0.0,
        _bracket_upper("initial_investment", b.initial_investment),
        b,
    )
    breakeven_rate_raw = _solve_breakeven("discount_rate", 0.001, 9.99, b)
    breakeven_rate = (
        round(breakeven_rate_raw * 100.0, 4) if breakeven_rate_raw is not None else None
    )

    breakeven_years: Optional[float] = None
    for years in range(1, 101):
        npv = calc_npv(
            b.initial_investment,
            b.operational_cost,
            b.expected_savings,
            years,
            b.discount_rate,
        )
        if npv >= 0:
            breakeven_years = float(years)
            break

    logger.info(
        "Break-even for '%s': savings=%s, investment=%s, rate=%s, years=%s",
        b.name,
        breakeven_savings,
        breakeven_investment,
        breakeven_rate,
        breakeven_years,
    )

    return BreakEvenResult(
        base_npv=base_npv,
        breakeven_savings=(round(breakeven_savings, 2) if breakeven_savings is not None else None),
        breakeven_investment=(
            round(breakeven_investment, 2) if breakeven_investment is not None else None
        ),
        breakeven_discount_rate=breakeven_rate,
        breakeven_years=breakeven_years,
    )
