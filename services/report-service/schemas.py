from pydantic import BaseModel
from typing import List, Optional


class FinancialData(BaseModel):
    name: str
    npv: float
    irr: float
    bcr: float
    simple_payback: float
    discounted_payback: float
    lcca: float
    yearly_details: Optional[List[dict]] = None


class EcoData(BaseModel):
    name: str
    co2_reduction_tons_per_year: float
    averted_damage_uah: float
    total_co2_value_usd: float


class RankingData(BaseModel):
    name: str
    consensus_rank: int
    rank_npv: int
    rank_co2: int
    rank_ahp: Optional[int] = None
    rank_topsis: Optional[int] = None


# ─── НОВІ поля для AHP/TOPSIS ─────────────────────
class AHPData(BaseModel):
    criteria: List[str]
    weights: List[float]
    consistency_ratio: float
    ranking: List[dict]


class TOPSISData(BaseModel):
    criteria: List[str]
    ranking: List[dict]


class SensitivityData(BaseModel):
    parameter: str
    impact_absolute: float = 0.0   # absolute NPV swing (currency units)
    impact_percent: float = 0.0    # relative swing (percent of |base NPV|)


class ReportInput(BaseModel):
    project_name: str
    project_description: Optional[str] = ""
    analyst_name: str
    financial_results: List[FinancialData]
    eco_results: List[EcoData]
    ranking: List[RankingData]
    best_measure: str
    recommendation: str
    # Опціональні нові секції
    ahp_data: Optional[AHPData] = None
    topsis_data: Optional[TOPSISData] = None
    sensitivity_data: Optional[List[SensitivityData]] = None