"""Unit tests for the scenario engine (what-if / sensitivity / break-even)."""

from __future__ import annotations

import math

import pytest

from tests.conftest import load_service

_sc = load_service("sc", "scenario-service", ["schemas", "calculator"])
schemas = _sc["schemas"]
calc = _sc["calculator"]

BaseScenario = schemas.BaseScenario
WhatIfInput = schemas.WhatIfInput
WhatIfParameter = schemas.WhatIfParameter
SensitivityInput = schemas.SensitivityInput
BreakEvenInput = schemas.BreakEvenInput


def _base(**overrides) -> BaseScenario:
    defaults = dict(
        name="Baseline",
        initial_investment=10_000,
        operational_cost=500,
        expected_savings=2_500,
        lifetime_years=10,
        discount_rate=0.08,
    )
    defaults.update(overrides)
    return BaseScenario(**defaults)


# ─── NPV ──────────────────────────────────────────────────────────────────────


def test_npv_zero_when_savings_match_investment():
    # Choose savings so that PV(annual_cf, r=0, n=5) = investment
    npv = calc.calc_npv(
        initial_investment=500,
        operational_cost=0,
        expected_savings=100,
        lifetime_years=5,
        discount_rate=0.0,
    )
    assert npv == 0.0


def test_npv_rejects_invalid_rate():
    with pytest.raises(ValueError):
        calc.calc_npv(100, 0, 100, 5, -1.5)


def test_npv_rejects_zero_lifetime():
    with pytest.raises(ValueError):
        calc.calc_npv(100, 0, 100, 0, 0.1)


# ─── What-if ──────────────────────────────────────────────────────────────────


def test_whatif_records_npv_change_and_percent():
    data = WhatIfInput(
        base=_base(),
        changes=[WhatIfParameter(parameter="expected_savings", new_value=5_000)],
    )
    results = calc.run_whatif(data)
    assert len(results) == 1
    r = results[0]
    assert r.parameter_changed == "expected_savings"
    assert r.new_npv > r.original_npv
    assert math.isclose(
        r.npv_change_percent,
        (r.npv_change / abs(r.original_npv)) * 100,
        abs_tol=0.1,
    )


def test_whatif_rejects_unknown_parameter():
    base = _base()
    # Bypass Pydantic field_validator to assert the calculator-level guard.
    data = WhatIfInput.model_construct(
        base=base,
        changes=[WhatIfParameter.model_construct(parameter="nope", new_value=1.0)],
    )
    with pytest.raises(ValueError):
        calc.run_whatif(data)


# ─── Sensitivity ──────────────────────────────────────────────────────────────


def test_sensitivity_returns_one_block_per_parameter():
    data = SensitivityInput(base=_base(), variation_percent=20.0, steps=3)
    res = calc.run_sensitivity(data)
    params = {r.parameter for r in res.results}
    assert params == {
        "expected_savings",
        "initial_investment",
        "discount_rate",
        "operational_cost",
        "lifetime_years",
    }


def test_sensitivity_orders_by_impact_descending():
    data = SensitivityInput(base=_base(), variation_percent=20.0, steps=3)
    res = calc.run_sensitivity(data)
    impacts = [r.impact_absolute for r in res.results]
    assert impacts == sorted(impacts, reverse=True)


def test_sensitivity_emits_2k_plus_1_points():
    data = SensitivityInput(base=_base(), variation_percent=10.0, steps=4)
    res = calc.run_sensitivity(data)
    for r in res.results:
        assert len(r.points) == 4 * 2 + 1


# ─── Break-even ───────────────────────────────────────────────────────────────


def test_breakeven_savings_recovers_investment_to_zero_npv():
    base = _base(expected_savings=2_500)
    res = calc.run_breakeven(BreakEvenInput(base=base))

    assert res.breakeven_savings is not None
    npv_at_root = calc.calc_npv(
        initial_investment=base.initial_investment,
        operational_cost=base.operational_cost,
        expected_savings=res.breakeven_savings,
        lifetime_years=base.lifetime_years,
        discount_rate=base.discount_rate,
    )
    assert abs(npv_at_root) < 1.0  # within 1 currency unit


def test_breakeven_years_is_first_year_npv_nonnegative():
    base = _base()
    res = calc.run_breakeven(BreakEvenInput(base=base))

    assert res.breakeven_years is not None
    y = int(res.breakeven_years)
    npv_at_y = calc.calc_npv(
        base.initial_investment,
        base.operational_cost,
        base.expected_savings,
        y,
        base.discount_rate,
    )
    npv_before = calc.calc_npv(
        base.initial_investment,
        base.operational_cost,
        base.expected_savings,
        max(1, y - 1),
        base.discount_rate,
    )
    assert npv_at_y >= 0
    if y > 1:
        assert npv_before < 0


def test_breakeven_unprofitable_project_returns_none_for_years():
    # Tiny savings, big investment → never breaks even within 100y
    base = _base(initial_investment=10_000_000, expected_savings=10)
    res = calc.run_breakeven(BreakEvenInput(base=base))
    assert res.breakeven_years is None
