"""Financial analysis — NPV, IRR, BCR, Payback, LCCA.

Numerical conventions:
  * ``cash_flows[0]`` is the (typically negative) initial outlay at t=0.
  * ``discount_rate`` is a per-period rate (0.10 = 10 %).
  * IRR is solved by Brent's method with explicit bracket detection;
    when no real root in (-99 %, +1000 %) exists ``IRRResult.value`` is
    ``None`` and ``converged`` is ``False`` instead of returning a magic
    sentinel like ``-1.0``.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from schemas import FinancialInput, FinancialResult, IRRResult, YearlyDetail
from scipy.optimize import brentq

logger = logging.getLogger(__name__)

_IRR_LOWER = -0.999  # > -100 %
_IRR_UPPER = 10.0  # +1000 %
_IRR_TOL = 1e-7
_IRR_MAXITER = 200


def _validate_inputs(data: FinancialInput) -> None:
    if data.lifetime_years < 1:
        raise ValueError("lifetime_years must be >= 1")
    if data.discount_rate <= -1.0:
        raise ValueError("discount_rate must be > -1 to avoid division by zero")
    if data.initial_investment < 0:
        raise ValueError("initial_investment must be non-negative")


def _npv(cash_flows: List[float], rate: float) -> float:
    if rate <= -1.0:
        raise ValueError("Discount rate <= -1 produces division by zero")
    factor = 1.0 + rate
    total = 0.0
    for t, cf in enumerate(cash_flows):
        total += cf / (factor**t)
    return total


def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
    return round(_npv(cash_flows, discount_rate), 2)


def calculate_irr(cash_flows: List[float]) -> IRRResult:
    if not cash_flows:
        return IRRResult(value=None, converged=False, iterations=0)
    has_pos = any(cf > 0 for cf in cash_flows)
    has_neg = any(cf < 0 for cf in cash_flows)
    if not (has_pos and has_neg):
        logger.debug("IRR undefined: cash flows do not change sign")
        return IRRResult(value=None, converged=False, iterations=0)

    def f(rate: float) -> float:
        return _npv(cash_flows, rate)

    try:
        f_low = f(_IRR_LOWER)
        f_high = f(_IRR_UPPER)
    except ValueError:
        return IRRResult(value=None, converged=False, iterations=0)

    if f_low * f_high > 0:
        logger.debug(
            "IRR not bracketed in [%.3f, %.1f]: f(low)=%.4f, f(high)=%.4f",
            _IRR_LOWER,
            _IRR_UPPER,
            f_low,
            f_high,
        )
        return IRRResult(value=None, converged=False, iterations=0)

    try:
        root, result = brentq(
            f,
            _IRR_LOWER,
            _IRR_UPPER,
            xtol=_IRR_TOL,
            maxiter=_IRR_MAXITER,
            full_output=True,
        )
    except (RuntimeError, ValueError) as exc:
        logger.warning("IRR brentq failed: %s", exc)
        return IRRResult(value=None, converged=False, iterations=_IRR_MAXITER)

    return IRRResult(
        value=round(float(root) * 100.0, 4),
        converged=bool(result.converged),
        iterations=int(result.iterations),
    )


def calculate_bcr(
    expected_savings: float,
    operational_cost: float,
    initial_investment: float,
    lifetime_years: int,
    discount_rate: float,
) -> Optional[float]:
    if discount_rate <= -1.0 or lifetime_years < 1:
        return None
    factor = 1.0 + discount_rate
    pv_savings = sum(expected_savings / (factor**t) for t in range(1, lifetime_years + 1))
    pv_opex = sum(operational_cost / (factor**t) for t in range(1, lifetime_years + 1))
    total_cost = initial_investment + pv_opex
    if total_cost <= 0:
        return None
    return round(pv_savings / total_cost, 4)


def calculate_simple_payback(
    annual_net_cash_flow: float, initial_investment: float
) -> Optional[float]:
    if annual_net_cash_flow <= 0:
        return None
    if initial_investment <= 0:
        return 0.0
    return round(initial_investment / annual_net_cash_flow, 4)


def calculate_discounted_payback(cash_flows: List[float], discount_rate: float) -> Optional[float]:
    if discount_rate <= -1.0 or len(cash_flows) < 2:
        return None
    factor = 1.0 + discount_rate
    cumulative = 0.0
    prev = 0.0
    for t, cf in enumerate(cash_flows):
        cumulative += cf / (factor**t)
        if t > 0 and cumulative >= 0:
            denom = cumulative - prev
            if denom == 0:
                return float(t)
            fraction = -prev / denom
            return round(float(t - 1 + fraction), 4)
        prev = cumulative
    return None


def calculate_lcca(
    initial_investment: float,
    operational_cost: float,
    lifetime_years: int,
    discount_rate: float,
) -> float:
    if discount_rate <= -1.0:
        raise ValueError("Discount rate <= -1 produces division by zero")
    factor = 1.0 + discount_rate
    pv_opex = sum(operational_cost / (factor**t) for t in range(1, lifetime_years + 1))
    return round(initial_investment + pv_opex, 2)


def build_yearly_details(
    annual_cf: float,
    initial_investment: float,
    lifetime_years: int,
    discount_rate: float,
) -> List[YearlyDetail]:
    details: List[YearlyDetail] = []
    factor = 1.0 + discount_rate
    cumulative = -initial_investment
    cumulative_disc = -initial_investment
    for year in range(1, lifetime_years + 1):
        discounted = annual_cf / (factor**year)
        cumulative += annual_cf
        cumulative_disc += discounted
        details.append(
            YearlyDetail(
                year=year,
                cash_flow=round(annual_cf, 2),
                discounted_cash_flow=round(discounted, 2),
                cumulative_cash_flow=round(cumulative, 2),
                cumulative_discounted=round(cumulative_disc, 2),
            )
        )
    return details


def analyze_measure(data: FinancialInput) -> FinancialResult:
    _validate_inputs(data)
    annual_net_cf = data.expected_savings - data.operational_cost
    cash_flows = [-data.initial_investment] + [annual_net_cf] * data.lifetime_years

    npv = calculate_npv(cash_flows, data.discount_rate)
    irr = calculate_irr(cash_flows)
    bcr = calculate_bcr(
        data.expected_savings,
        data.operational_cost,
        data.initial_investment,
        data.lifetime_years,
        data.discount_rate,
    )
    simple_pb = calculate_simple_payback(annual_net_cf, data.initial_investment)
    disc_pb = calculate_discounted_payback(cash_flows, data.discount_rate)
    lcca = calculate_lcca(
        data.initial_investment,
        data.operational_cost,
        data.lifetime_years,
        data.discount_rate,
    )
    yearly = build_yearly_details(
        annual_net_cf,
        data.initial_investment,
        data.lifetime_years,
        data.discount_rate,
    )

    logger.info(
        "Financial analysis '%s': NPV=%.2f, IRR=%s, BCR=%s, payback=%s yr",
        data.name,
        npv,
        f"{irr.value:.2f}%" if irr.value is not None else "N/A",
        f"{bcr:.4f}" if bcr is not None else "N/A",
        f"{simple_pb:.2f}" if simple_pb is not None else "N/A",
    )

    return FinancialResult(
        name=data.name,
        npv=npv,
        irr=irr,
        bcr=bcr,
        simple_payback=simple_pb,
        discounted_payback=disc_pb,
        lcca=lcca,
        yearly_details=yearly,
    )
