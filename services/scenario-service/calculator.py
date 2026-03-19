import logging
from typing import List
import numpy as np
from schemas import (
    BaseScenario, WhatIfInput, WhatIfResult,
    SensitivityInput, SensitivityAnalysisResult, SensitivityResult, SensitivityPoint,
    BreakEvenInput, BreakEvenResult
)

logger = logging.getLogger(__name__)


def calc_npv(initial_investment: float, operational_cost: float,
             expected_savings: float, lifetime_years: int,
             discount_rate: float) -> float:
    """Розраховує NPV для заданих параметрів"""
    annual_cf = expected_savings - operational_cost
    cash_flows = [-initial_investment] + [annual_cf] * lifetime_years
    npv = sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows))
    return round(npv, 2)


def run_whatif(data: WhatIfInput) -> List[WhatIfResult]:
    """
    What-if аналіз: перераховує NPV при зміні кожного параметру
    """
    b = data.base
    base_npv = calc_npv(
        b.initial_investment, b.operational_cost,
        b.expected_savings, b.lifetime_years, b.discount_rate
    )

    results = []
    for change in data.changes:
        # Копіюємо базові параметри
        params = {
            "initial_investment": b.initial_investment,
            "operational_cost": b.operational_cost,
            "expected_savings": b.expected_savings,
            "lifetime_years": b.lifetime_years,
            "discount_rate": b.discount_rate
        }

        original_value = params.get(change.parameter, 0)

        # Змінюємо один параметр
        if change.parameter in params:
            params[change.parameter] = change.new_value

        new_npv = calc_npv(**params)
        npv_change = new_npv - base_npv
        npv_change_pct = (npv_change / abs(base_npv) * 100) if base_npv != 0 else 0

        results.append(WhatIfResult(
            name=b.name,
            parameter_changed=change.parameter,
            original_value=original_value,
            new_value=change.new_value,
            original_npv=base_npv,
            new_npv=new_npv,
            npv_change=round(npv_change, 2),
            npv_change_percent=round(npv_change_pct, 2)
        ))

    return results


def run_sensitivity(data: SensitivityInput) -> SensitivityAnalysisResult:
    """
    Sensitivity Analysis з tornado chart даними.
    Варіює кожен параметр від -variation% до +variation%.
    impact_percent у результаті зберігає абсолютну різницю NPV (грн) —
    назва поля збережена для сумісності API.
    """
    b = data.base
    base_npv = calc_npv(
        b.initial_investment, b.operational_cost,
        b.expected_savings, b.lifetime_years, b.discount_rate
    )

    # Параметри для аналізу чутливості
    parameters = {
        "expected_savings": b.expected_savings,
        "initial_investment": b.initial_investment,
        "discount_rate": b.discount_rate,
        "operational_cost": b.operational_cost,
        "lifetime_years": float(b.lifetime_years)
    }

    sensitivity_results = []
    v = data.variation_percent / 100

    for param_name, base_value in parameters.items():
        points = []
        npv_values = []

        # Генеруємо точки від -v до +v
        variations = np.linspace(-v, v, data.steps * 2 + 1)

        for var in variations:
            params = {
                "initial_investment": b.initial_investment,
                "operational_cost": b.operational_cost,
                "expected_savings": b.expected_savings,
                "lifetime_years": b.lifetime_years,
                "discount_rate": b.discount_rate
            }

            # Якщо базове значення = 0 — застосовуємо абсолютний зсув замість відносного
            if base_value == 0:
                # Використовуємо невелике абсолютне значення для варіації
                abs_delta = {"initial_investment": 10000, "operational_cost": 1000,
                             "expected_savings": 1000, "discount_rate": 0.01, "lifetime_years": 1}
                new_value = abs_delta.get(param_name, 1000) * var
            else:
                new_value = base_value * (1 + var)

            # Lifetime years — тільки цілі числа
            if param_name == "lifetime_years":
                params[param_name] = max(1, int(round(new_value)))
            elif param_name == "discount_rate":
                params[param_name] = max(0.001, new_value)
            else:
                params[param_name] = max(0, new_value)

            npv = calc_npv(**params)
            npv_values.append(npv)

            points.append(SensitivityPoint(
                variation_percent=round(var * 100, 1),
                value=round(new_value, 4),
                npv=npv
            ))

        # Вплив = абсолютна різниця між макс і мін NPV (грн, для tornado chart)
        # Поле називається impact_percent для сумісності API, але зберігає UAH-значення
        impact = max(npv_values) - min(npv_values)

        sensitivity_results.append(SensitivityResult(
            parameter=param_name,
            base_value=base_value,
            base_npv=base_npv,
            impact_percent=round(impact, 2),  # UAH (absolute NPV range)
            points=points
        ))

    # Сортуємо за впливом (для tornado chart — найвпливовіший вгорі)
    sensitivity_results.sort(key=lambda x: x.impact_percent, reverse=True)

    logger.info(
        "Sensitivity analysis for '%s': base_npv=%.2f, top param='%s'",
        b.name, base_npv,
        sensitivity_results[0].parameter if sensitivity_results else "N/A"
    )

    return SensitivityAnalysisResult(
        base_npv=base_npv,
        results=sensitivity_results
    )


def _bisect_npv(param_name: str, low: float, high: float,
                base: BaseScenario, max_iter: int = 1000,
                tol: float = 1.0) -> float:
    """
    Допоміжна функція бісекції: шукає значення param_name при якому NPV ≈ 0.
    Повертає знайдене значення або -1.0 якщо не вдалось bracketed.
    """
    def npv_for(val: float) -> float:
        params = {
            "initial_investment": base.initial_investment,
            "operational_cost": base.operational_cost,
            "expected_savings": base.expected_savings,
            "lifetime_years": base.lifetime_years,
            "discount_rate": base.discount_rate,
        }
        params[param_name] = val
        return calc_npv(**params)

    npv_low = npv_for(low)
    npv_high = npv_for(high)

    # Перевіряємо чи bracketed
    if npv_low * npv_high > 0:
        logger.warning(
            "Break-even bisection for '%s' not bracketed: NPV(%.2f)=%.2f, NPV(%.2f)=%.2f",
            param_name, low, npv_low, high, npv_high
        )
        return -1.0

    mid = low
    for _ in range(max_iter):
        mid = (low + high) / 2
        npv_mid = npv_for(mid)

        if abs(npv_mid) < tol:
            break

        if npv_low * npv_mid < 0:
            high = mid
        else:
            low = mid
            npv_low = npv_mid

    return mid


def run_breakeven(data: BreakEvenInput) -> BreakEvenResult:
    """
    Break-even аналіз: знаходить порогові значення при яких NPV = 0
    """
    b = data.base
    base_npv = calc_npv(
        b.initial_investment, b.operational_cost,
        b.expected_savings, b.lifetime_years, b.discount_rate
    )

    # 1. Мінімальна економія при NPV = 0
    # savings збільшення → NPV зростає → [0, savings*10] охоплює корінь
    breakeven_savings = _bisect_npv(
        "expected_savings",
        low=0.0,
        high=b.expected_savings * 10,
        base=b
    )

    # 2. Максимальна інвестиція при NPV = 0
    # investment збільшення → NPV падає → [0, investment*10] охоплює корінь
    breakeven_investment = _bisect_npv(
        "initial_investment",
        low=0.0,
        high=b.initial_investment * 10,
        base=b
    )

    # 3. Максимальна ставка дисконтування при NPV = 0 (= IRR)
    breakeven_rate_raw = _bisect_npv(
        "discount_rate",
        low=0.001,
        high=9.99,
        base=b
    )
    breakeven_rate = round(breakeven_rate_raw * 100, 2) if breakeven_rate_raw > 0 else -1.0

    # 4. Мінімальний термін при NPV = 0 (лінійний пошук, достатній для 1–100 років)
    breakeven_years = -1.0
    for years in range(1, 101):
        npv = calc_npv(b.initial_investment, b.operational_cost,
                       b.expected_savings, years, b.discount_rate)
        if npv >= 0:
            breakeven_years = float(years)
            break

    logger.info(
        "Break-even for '%s': savings=%.2f, investment=%.2f, rate=%.2f%%, years=%.0f",
        b.name, breakeven_savings, breakeven_investment, breakeven_rate, breakeven_years
    )

    return BreakEvenResult(
        base_npv=base_npv,
        breakeven_savings=round(breakeven_savings, 2),
        breakeven_investment=round(breakeven_investment, 2),
        breakeven_discount_rate=breakeven_rate,
        breakeven_years=breakeven_years
    )
