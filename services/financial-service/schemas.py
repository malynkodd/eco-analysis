from pydantic import BaseModel
from typing import List


class FinancialInput(BaseModel):
    """Вхідні дані для фінансового аналізу одного заходу"""
    name: str
    initial_investment: float      # початкові інвестиції (грн)
    operational_cost: float        # операційні витрати на рік (грн)
    expected_savings: float        # очікувана економія на рік (грн)
    lifetime_years: int            # термін експлуатації (років)
    discount_rate: float = 0.1     # ставка дисконтування (10% за замовч.)


class YearlyDetail(BaseModel):
    """Деталізація по кожному року"""
    year: int
    cash_flow: float               # грошовий потік
    discounted_cash_flow: float    # дисконтований грошовий потік
    cumulative_cash_flow: float    # кумулятивний грошовий потік
    cumulative_discounted: float   # кумулятивний дисконтований


class FinancialResult(BaseModel):
    """Результати фінансового аналізу"""
    name: str
    npv: float                     # чиста приведена вартість
    irr: float                     # внутрішня норма дохідності
    bcr: float                     # benefit-cost ratio
    simple_payback: float          # простий термін окупності (років)
    discounted_payback: float      # дисконтований термін окупності (років)
    lcca: float                    # вартість життєвого циклу
    yearly_details: List[YearlyDetail]


class PortfolioInput(BaseModel):
    """Портфель заходів для порівняльного аналізу"""
    measures: List[FinancialInput]
    discount_rate: float = 0.1


class PortfolioResult(BaseModel):
    """Результати аналізу портфелю"""
    results: List[FinancialResult]