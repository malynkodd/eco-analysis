from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, validator


class FuelType(str, Enum):
    natural_gas = "natural_gas"  # природний газ
    electricity = "electricity"  # електроенергія
    coal = "coal"  # вугілля
    diesel = "diesel"  # дизельне паливо
    heating_oil = "heating_oil"  # мазут


class MeasureType(str, Enum):
    """Тип заходу — впливає на вибір емісійних коефіцієнтів і категорій впливу."""

    insulation = "insulation"
    equipment_replacement = "equipment_replacement"
    treatment_facility = "treatment_facility"
    renewable_energy = "renewable_energy"
    process_optimisation = "process_optimisation"
    transport = "transport"


class PollutantCategory(str, Enum):
    """Категорії забруднення для регуляторної методики (UA/EU)."""

    co2 = "co2"
    nox = "nox"
    sox = "sox"
    pm = "pm"  # particulate matter (PM2.5/PM10)
    voc = "voc"


class EcoInput(BaseModel):
    """Вхідні дані для оцінки екологічного ефекту"""

    name: str
    fuel_type: FuelType
    annual_consumption_reduction: float  # зменшення споживання (кВт·год або м³/рік)
    co2_price_per_ton: float = 30.0  # ціна тонни CO2 (USD, за замовч. $30)
    damage_coefficient: float = 100.0  # коефіцієнт відверненого збитку (грн/т)
    # Optional fields enabling project-level "cost per tonne CO2 reduction"
    initial_investment: float = 0.0  # сумарні капвитрати (грн), для cost/tCO2
    lifespan_years: int = 0  # термін експлуатації (роки), 0 = не рахувати
    # Optional regulatory pricing — when provided, replaces simple coefficient.
    # `regulatory_methodology` ∈ {"UA", "EU", "custom"}. UA — Ministry of
    # Environmental Protection of Ukraine; EU — ExternE / EEA damage costs.
    regulatory_methodology: Optional[str] = None
    measure_type: Optional[MeasureType] = None
    pollutant_categories: Optional[List[PollutantCategory]] = None

    @validator("annual_consumption_reduction")
    def consumption_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("annual_consumption_reduction must be greater than 0")
        return v

    @validator("co2_price_per_ton")
    def co2_price_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("co2_price_per_ton must be >= 0")
        return v

    @validator("damage_coefficient")
    def damage_coeff_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("damage_coefficient must be >= 0")
        return v

    @validator("regulatory_methodology")
    def methodology_must_be_known(cls, v):
        if v is None:
            return v
        if v not in ("UA", "EU", "custom"):
            raise ValueError("regulatory_methodology must be one of: UA, EU, custom")
        return v


class EcoResult(BaseModel):
    """Результати оцінки екологічного ефекту"""

    name: str
    co2_reduction_tons_per_year: float  # зменшення CO2 (т/рік)
    carbon_footprint_reduction: float  # вуглецевий слід (т CO2-екв/рік)
    averted_damage_uah: float  # відвернений збиток (грн/рік)
    co2_cost_per_ton: float  # вартість тонни CO2 (USD/т)
    total_co2_value_usd: float  # загальна вартість зменшення CO2 (USD/рік)
    emission_factor: float  # коефіцієнт емісії (кг CO2/кВт·год або м³)
    cost_per_tonne_reduction_uah: Optional[float] = None  # грн / тCO2 за весь lifespan
    methodology: Optional[str] = None  # регуляторна методика (UA/EU/custom/legacy)
    pollutant_breakdown: Optional[dict] = None  # розподіл збитку за забрудниками


class PortfolioEcoInput(BaseModel):
    """Портфель заходів для порівняльного аналізу"""

    measures: List[EcoInput]


class PortfolioEcoResult(BaseModel):
    results: List[EcoResult]
    total_co2_reduction: float  # загальне зменшення CO2 (т/рік)
    total_averted_damage_uah: float  # загальний відвернений збиток (грн/рік)
