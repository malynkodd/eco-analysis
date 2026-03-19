import logging
from fastapi import HTTPException, status
from schemas import EcoInput, EcoResult, FuelType

logger = logging.getLogger(__name__)

# ─── Коефіцієнти емісії CO2 (кг CO2 на одиницю споживання) ───────────────────
# Джерело: IPCC, Мінприроди України
EMISSION_FACTORS = {
    FuelType.natural_gas:  2.04,   # кг CO2/м³ природного газу
    FuelType.electricity:  0.37,   # кг CO2/кВт·год (середнє по Україні)
    FuelType.coal:         2.86,   # кг CO2/кг вугілля
    FuelType.diesel:       2.68,   # кг CO2/літр дизелю
    FuelType.heating_oil:  3.15,   # кг CO2/кг мазуту
}

# GWP коефіцієнти для CO2-еквіваленту (CO2 = 1.0)
GWP_CO2 = 1.0


def calculate_eco_impact(data: EcoInput) -> EcoResult:
    """
    Розраховує екологічний ефект заходу:
    1. Зменшення CO2 (т/рік)
    2. Carbon Footprint (т CO2-екв/рік)
    3. Відвернений екологічний збиток (грн/рік)
    4. Вартість тонни CO2 для порівняння
    """
    # Коефіцієнт емісії для даного виду палива (захист від KeyError)
    emission_factor = EMISSION_FACTORS.get(data.fuel_type)
    if emission_factor is None:
        logger.error("Unknown fuel type: %s", data.fuel_type)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown fuel type: {data.fuel_type}. "
                   f"Allowed: {[f.value for f in FuelType]}"
        )

    # annual_consumption_reduction > 0 гарантовано валідатором у schemas.py
    # Зменшення CO2 (переводимо кг → тонни)
    co2_reduction_kg = data.annual_consumption_reduction * emission_factor
    co2_reduction_tons = co2_reduction_kg / 1000

    # Carbon Footprint reduction (з урахуванням GWP)
    carbon_footprint = co2_reduction_tons * GWP_CO2

    # Відвернений екологічний збиток (грн/рік)
    # Формула: зменшення CO2 (т) × коефіцієнт збитку (грн/т)
    averted_damage = co2_reduction_tons * data.damage_coefficient

    # Загальна вартість зменшення CO2 (USD/рік)
    total_co2_value = co2_reduction_tons * data.co2_price_per_ton

    logger.info(
        "Eco impact calculated for '%s': CO2=%.3f t/yr, damage=%.2f UAH/yr",
        data.name, co2_reduction_tons, averted_damage
    )

    return EcoResult(
        name=data.name,
        co2_reduction_tons_per_year=round(co2_reduction_tons, 3),
        carbon_footprint_reduction=round(carbon_footprint, 3),
        averted_damage_uah=round(averted_damage, 2),
        co2_cost_per_ton=data.co2_price_per_ton,
        total_co2_value_usd=round(total_co2_value, 2),
        emission_factor=emission_factor
    )
