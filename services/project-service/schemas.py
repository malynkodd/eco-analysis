from pydantic import BaseModel, validator
from typing import List, Optional
from enum import Enum


class MeasureType(str, Enum):
    insulation = "insulation"
    equipment = "equipment"
    treatment = "treatment"
    renewable = "renewable"


# ─── Measure схеми ────────────────────────────────────
class MeasureCreate(BaseModel):
    name: str
    measure_type: MeasureType
    initial_investment: float
    operational_cost: float
    expected_savings: float
    lifetime_years: int
    emission_reduction: float


class MeasureResponse(BaseModel):
    id: int
    project_id: int
    name: str
    measure_type: str
    initial_investment: float
    operational_cost: float
    expected_savings: float
    lifetime_years: int
    emission_reduction: float

    class Config:
        from_attributes = True


# ─── Project схеми ────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_username: str
    status: str = "pending"
    manager_comment: Optional[str] = None
    measures: List[MeasureResponse] = []

    class Config:
        from_attributes = True


# ─── Статус затвердження ───────────────────────────────
class StatusUpdate(BaseModel):
    """Тіло запиту для зміни статусу проєкту (тільки менеджер/адмін)"""
    status: str
    manager_comment: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        allowed = ('approved', 'rejected', 'pending')
        if v not in allowed:
            raise ValueError(f"status must be one of: {allowed}")
        return v
