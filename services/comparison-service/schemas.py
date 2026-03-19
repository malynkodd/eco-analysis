from pydantic import BaseModel
from typing import List, Optional


class MeasureData(BaseModel):
    """Дані одного заходу з результатами всіх методів аналізу"""
    name: str

    # Фінансові показники
    npv: float
    irr: float
    bcr: float
    simple_payback: float

    # Екологічний показник
    co2_reduction: float

    # Багатокритеріальні оцінки (опціональні)
    ahp_score: Optional[float] = None
    topsis_score: Optional[float] = None


class RankingRow(BaseModel):
    """Рядок зведеної таблиці рангів"""
    name: str
    rank_npv: int
    rank_irr: int
    rank_bcr: int
    rank_payback: int
    rank_co2: int
    rank_ahp: Optional[int] = None
    rank_topsis: Optional[int] = None
    consensus_score: float       # консенсусний рейтинг
    consensus_rank: int          # фінальне місце


class ParetoItem(BaseModel):
    """Елемент Pareto-аналізу"""
    name: str
    npv: float
    co2_reduction: float
    is_pareto_optimal: bool      # True якщо не домінується жодним іншим


class ComparisonInput(BaseModel):
    measures: List[MeasureData]


class ComparisonResult(BaseModel):
    ranking_table: List[RankingRow]
    pareto_front: List[ParetoItem]
    best_financial: str          # найкращий за NPV
    best_ecological: str         # найкращий за CO2
    best_consensus: str          # найкращий за консенсусом
    conflicting: List[str]       # заходи з суперечливою пріоритизацією