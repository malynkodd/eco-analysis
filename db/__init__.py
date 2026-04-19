"""Shared persistence layer for the eco-analysis platform.

This package owns the single source of truth for SQLAlchemy models, the
declarative base, the engine factory, the session factory, and the
``get_db`` FastAPI dependency. Every microservice imports from here
instead of defining its own models.

Imported once per process; the engine is created lazily on first use so
unit tests that never touch the DB do not need ``DATABASE_URL`` set.
"""

from db.base import Base, SessionLocal, engine, get_db, init_engine
from db.models import (
    AHPResult,
    ComparisonResult,
    EcoResult,
    FinancialResult,
    Measure,
    MeasureType,
    Project,
    ProjectStatus,
    ScenarioResult,
    TopsisResult,
    User,
    UserRole,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "init_engine",
    "User",
    "UserRole",
    "Project",
    "ProjectStatus",
    "Measure",
    "MeasureType",
    "FinancialResult",
    "AHPResult",
    "TopsisResult",
    "EcoResult",
    "ScenarioResult",
    "ComparisonResult",
]
