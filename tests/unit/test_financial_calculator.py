"""Unit tests for the financial calculator (NPV / IRR / BCR / payback / LCCA)."""
from __future__ import annotations

import math

import pytest

from tests.conftest import load_service

_fin = load_service("fin", "financial-service", ["schemas", "calculator"])
schemas = _fin["schemas"]
calc = _fin["calculator"]

FinancialInput = schemas.FinancialInput


# ─── NPV ──────────────────────────────────────────────────────────────────────


def test_npv_with_zero_rate_is_simple_sum():
    cf = [-100.0, 30.0, 30.0, 30.0, 30.0]
    assert calc.calculate_npv(cf, 0.0) == 20.0


def test_npv_decreases_with_higher_rate():
    cf = [-1000.0, 400.0, 400.0, 400.0]
    npv_low = calc.calculate_npv(cf, 0.05)
    npv_high = calc.calculate_npv(cf, 0.20)
    assert npv_low > npv_high


# ─── IRR ──────────────────────────────────────────────────────────────────────


def test_irr_zero_when_pv_savings_equals_outlay():
    # NPV = -100 + 110/(1+r) = 0  =>  r = 0.10
    cf = [-100.0, 110.0]
    irr = calc.calculate_irr(cf)
    assert irr.converged
    assert math.isclose(irr.value, 10.0, abs_tol=1e-2)


def test_irr_returns_none_when_no_sign_change():
    irr = calc.calculate_irr([100.0, 50.0, 50.0])  # all positive
    assert irr.value is None
    assert not irr.converged


def test_irr_returns_none_for_empty_cash_flows():
    irr = calc.calculate_irr([])
    assert irr.value is None
    assert irr.iterations == 0


def test_irr_converges_for_realistic_project():
    # 10-year project, NPV positive at 5 %, negative at 50 % → IRR in between
    cf = [-1000.0] + [200.0] * 10
    irr = calc.calculate_irr(cf)
    assert irr.converged
    assert 10.0 < irr.value < 25.0


# ─── BCR ──────────────────────────────────────────────────────────────────────


def test_bcr_above_one_for_profitable_measure():
    bcr = calc.calculate_bcr(
        expected_savings=300, operational_cost=50,
        initial_investment=1000, lifetime_years=10, discount_rate=0.05,
    )
    assert bcr is not None
    assert bcr > 1.0


def test_bcr_none_for_zero_costs():
    assert calc.calculate_bcr(100, 0, 0, 5, 0.1) is None


# ─── Payback ──────────────────────────────────────────────────────────────────


def test_simple_payback_returns_none_for_non_positive_cash_flow():
    assert calc.calculate_simple_payback(0.0, 100) is None
    assert calc.calculate_simple_payback(-50.0, 100) is None


def test_simple_payback_zero_when_no_outlay():
    assert calc.calculate_simple_payback(100.0, 0.0) == 0.0


def test_simple_payback_basic():
    assert calc.calculate_simple_payback(250.0, 1000.0) == 4.0


def test_discounted_payback_longer_than_simple():
    cf = [-1000.0] + [300.0] * 5
    simple = calc.calculate_simple_payback(300.0, 1000.0)
    discounted = calc.calculate_discounted_payback(cf, 0.10)
    assert discounted is not None
    assert discounted > simple


def test_discounted_payback_none_when_never_recovers():
    cf = [-1000.0] + [10.0] * 3
    assert calc.calculate_discounted_payback(cf, 0.10) is None


# ─── LCCA ─────────────────────────────────────────────────────────────────────


def test_lcca_includes_initial_plus_discounted_opex():
    lcca = calc.calculate_lcca(
        initial_investment=1000, operational_cost=100,
        lifetime_years=5, discount_rate=0.10,
    )
    pv_opex = sum(100 / (1.10 ** t) for t in range(1, 6))
    assert math.isclose(lcca, round(1000 + pv_opex, 2), abs_tol=0.01)


def test_lcca_rejects_invalid_rate():
    with pytest.raises(ValueError):
        calc.calculate_lcca(1000, 100, 5, -1.5)


# ─── End-to-end analyze_measure ───────────────────────────────────────────────


def test_analyze_measure_populates_all_fields():
    inp = FinancialInput(
        name="Insulation",
        initial_investment=10_000,
        operational_cost=500,
        expected_savings=2_500,
        lifetime_years=10,
        discount_rate=0.08,
    )
    result = calc.analyze_measure(inp)

    assert result.name == "Insulation"
    assert result.npv != 0
    assert result.irr.converged
    assert result.bcr is not None
    assert result.simple_payback is not None
    assert result.lcca > inp.initial_investment
    assert len(result.yearly_details) == 10


def test_analyze_measure_rejects_zero_lifetime():
    with pytest.raises(Exception):
        FinancialInput(
            name="X", initial_investment=1, operational_cost=0,
            expected_savings=1, lifetime_years=0, discount_rate=0.1,
        )
