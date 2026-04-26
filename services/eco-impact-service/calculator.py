import logging
from typing import Optional

from fastapi import HTTPException, status
from schemas import EcoInput, EcoResult, FuelType, PollutantCategory

logger = logging.getLogger(__name__)

# ─── Коефіцієнти емісії CO2 (кг CO2 на одиницю споживання) ───────────────────
# Джерело: IPCC AR6 (2021), Національний кадастр України 2022
EMISSION_FACTORS = {
    FuelType.natural_gas: 2.04,  # кг CO2/м³ природного газу
    FuelType.electricity: 0.37,  # кг CO2/кВт·год (середнє по Україні)
    FuelType.coal: 2.86,  # кг CO2/кг вугілля
    FuelType.diesel: 2.68,  # кг CO2/літр дизелю
    FuelType.heating_oil: 3.15,  # кг CO2/кг мазуту
}

# GWP коефіцієнти для CO2-еквіваленту (IPCC AR6, 100-year horizon)
GWP_CO2 = 1.0

# ─── Регуляторні ставки збитку від забруднення (грн/тонну) ───────────────────
# UA: Постанова КМУ №1051 / Методика Мінприроди визначення розмірів збитків.
# EU: ExternE / European Environment Agency damage cost handbook (2014, оновл. 2019).
# Коефіцієнти представлено в грн/т для уніфікації; курс EUR=42 UAH (станом 2024).
REGULATORY_DAMAGE_COEFF_UAH_PER_TON = {
    "UA": {
        PollutantCategory.co2: 875.0,        # грн/т CO2 — постановна оцінка
        PollutantCategory.nox: 18900.0,      # грн/т NOx
        PollutantCategory.sox: 24090.0,      # грн/т SOx
        PollutantCategory.pm: 28560.0,       # грн/т PM (тверді частинки)
        PollutantCategory.voc: 12180.0,      # грн/т ЛОС
    },
    "EU": {
        PollutantCategory.co2: 4200.0,       # ≈100 EUR/т (CE Delft 2018)
        PollutantCategory.nox: 504000.0,     # ≈12000 EUR/т
        PollutantCategory.sox: 462000.0,     # ≈11000 EUR/т
        PollutantCategory.pm: 1680000.0,     # ≈40000 EUR/т (PM2.5 health cost)
        PollutantCategory.voc: 84000.0,      # ≈2000 EUR/т
    },
}

# ─── Спів-емісійні фактори (тонн забруднювача / тонну CO2) для палив ─────────
# Дозволяє автоматично оцінити NOx/SOx/PM/VOC paralelно зі зменшенням CO2.
COFACTORS_PER_TCO2 = {
    FuelType.natural_gas: {
        PollutantCategory.nox: 0.0009,
        PollutantCategory.sox: 0.000005,
        PollutantCategory.pm: 0.00002,
        PollutantCategory.voc: 0.00005,
    },
    FuelType.electricity: {
        PollutantCategory.nox: 0.0021,
        PollutantCategory.sox: 0.0048,
        PollutantCategory.pm: 0.00045,
        PollutantCategory.voc: 0.00006,
    },
    FuelType.coal: {
        PollutantCategory.nox: 0.0035,
        PollutantCategory.sox: 0.0095,
        PollutantCategory.pm: 0.0011,
        PollutantCategory.voc: 0.00015,
    },
    FuelType.diesel: {
        PollutantCategory.nox: 0.0140,
        PollutantCategory.sox: 0.0006,
        PollutantCategory.pm: 0.00080,
        PollutantCategory.voc: 0.00120,
    },
    FuelType.heating_oil: {
        PollutantCategory.nox: 0.0050,
        PollutantCategory.sox: 0.0180,
        PollutantCategory.pm: 0.00100,
        PollutantCategory.voc: 0.00050,
    },
}


def _averted_damage_regulatory(
    co2_reduction_tons: float,
    fuel_type: FuelType,
    methodology: str,
    categories: Optional[list],
) -> tuple[float, dict]:
    """Compute averted damage using a regulatory coefficient table.

    Returns (total_damage_uah, breakdown_per_pollutant).
    """
    table = REGULATORY_DAMAGE_COEFF_UAH_PER_TON[methodology]
    cofactors = COFACTORS_PER_TCO2.get(fuel_type, {})
    cats = categories or [PollutantCategory.co2]
    breakdown: dict = {}
    total = 0.0
    for cat in cats:
        if cat == PollutantCategory.co2:
            tons = co2_reduction_tons
        else:
            tons = co2_reduction_tons * cofactors.get(cat, 0.0)
        damage = tons * table.get(cat, 0.0)
        breakdown[cat.value if hasattr(cat, "value") else str(cat)] = round(damage, 2)
        total += damage
    return total, breakdown


def calculate_eco_impact(data: EcoInput) -> EcoResult:
    """
    Розраховує екологічний ефект заходу:
    1. Зменшення CO2 (т/рік)
    2. Carbon Footprint (т CO2-екв/рік)
    3. Відвернений екологічний збиток (грн/рік) — UA/EU методика, або legacy coeff
    4. Вартість тонни CO2 для порівняння
    5. Cost per tonne CO2 reduction (грн/тCO2 за lifespan) — якщо вказано investment+lifespan
    """
    # Коефіцієнт емісії для даного виду палива (захист від KeyError)
    emission_factor = EMISSION_FACTORS.get(data.fuel_type)
    if emission_factor is None:
        logger.error("Unknown fuel type: %s", data.fuel_type)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown fuel type: {data.fuel_type}. Allowed: {[f.value for f in FuelType]}",
        )

    # annual_consumption_reduction > 0 гарантовано валідатором у schemas.py
    # Зменшення CO2 (переводимо кг → тонни)
    co2_reduction_kg = data.annual_consumption_reduction * emission_factor
    co2_reduction_tons = co2_reduction_kg / 1000

    # Carbon Footprint reduction (з урахуванням GWP)
    carbon_footprint = co2_reduction_tons * GWP_CO2

    # Відвернений екологічний збиток (грн/рік)
    methodology = data.regulatory_methodology
    breakdown: Optional[dict] = None
    if methodology in ("UA", "EU"):
        averted_damage, breakdown = _averted_damage_regulatory(
            co2_reduction_tons,
            data.fuel_type,
            methodology,
            data.pollutant_categories,
        )
    else:
        # Legacy / custom path: simple linear coefficient
        averted_damage = co2_reduction_tons * data.damage_coefficient
        methodology = methodology or "legacy"

    # Загальна вартість зменшення CO2 (USD/рік) — ринкова ціна вуглецю
    total_co2_value = co2_reduction_tons * data.co2_price_per_ton

    # Cost per tonne CO2 reduction за весь життєвий цикл проєкту:
    #   total_project_cost / (annual_CO2_reduction × lifespan)
    cost_per_tonne: Optional[float] = None
    if (
        data.initial_investment > 0
        and data.lifespan_years > 0
        and co2_reduction_tons > 0
    ):
        denom = co2_reduction_tons * data.lifespan_years
        cost_per_tonne = round(data.initial_investment / denom, 2)

    logger.info(
        "Eco impact '%s': CO2=%.3f t/yr, damage=%.2f UAH/yr (methodology=%s)",
        data.name,
        co2_reduction_tons,
        averted_damage,
        methodology,
    )

    return EcoResult(
        name=data.name,
        co2_reduction_tons_per_year=round(co2_reduction_tons, 3),
        carbon_footprint_reduction=round(carbon_footprint, 3),
        averted_damage_uah=round(averted_damage, 2),
        co2_cost_per_ton=data.co2_price_per_ton,
        total_co2_value_usd=round(total_co2_value, 2),
        emission_factor=emission_factor,
        cost_per_tonne_reduction_uah=cost_per_tonne,
        methodology=methodology,
        pollutant_breakdown=breakdown,
    )
