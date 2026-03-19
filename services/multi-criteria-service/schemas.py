from pydantic import BaseModel
from typing import List, Optional


class AHPInput(BaseModel):
    """
    Вхідні дані для методу AHP.
    criteria — список назв критеріїв
    comparison_matrix — матриця парних порівнянь (шкала Сааті 1-9)
    alternatives — список альтернатив з оцінками по кожному критерію
    """
    criteria: List[str]
    comparison_matrix: List[List[float]]
    alternatives: List[dict]


class AHPResult(BaseModel):
    criteria: List[str]
    weights: List[float]              # ваги критеріїв
    consistency_ratio: float          # CR — має бути < 0.1
    is_consistent: bool               # True якщо CR < 0.1
    ranking: List[dict]               # рейтинг альтернатив


class TOPSISInput(BaseModel):
    """
    Вхідні дані для методу TOPSIS.
    criteria — назви критеріїв
    weights — ваги критеріїв (сума = 1)
    is_benefit — True якщо критерій вигідний (більше = краще)
    alternatives — матриця рішень
    """
    criteria: List[str]
    weights: List[float]
    is_benefit: List[bool]
    alternatives: List[dict]


class TOPSISResult(BaseModel):
    criteria: List[str]
    weights: List[float]
    ranking: List[dict]               # рейтинг з коефіцієнтом близькості


class CombinedInput(BaseModel):
    """Комбінований аналіз AHP + TOPSIS"""
    criteria: List[str]
    comparison_matrix: List[List[float]]
    is_benefit: List[bool]
    alternatives: List[dict]


class CombinedResult(BaseModel):
    ahp: AHPResult
    topsis: TOPSISResult