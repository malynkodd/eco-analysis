"""SQLAlchemy 2.0 models for the entire eco-analysis platform.

Single source of truth — every microservice imports from this module
rather than defining duplicate model classes. All result tables use
JSONB so the calculator services can persist arbitrary input/output
payloads without schema churn.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

# ─── Enums ───────────────────────────────────────────────────────────────────


class UserRole(str, enum.Enum):
    analyst = "analyst"
    manager = "manager"
    admin = "admin"


class ProjectStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class MeasureType(str, enum.Enum):
    insulation = "insulation"
    equipment = "equipment"
    treatment = "treatment"
    renewable = "renewable"


# ─── Identity ────────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.analyst,
        server_default=UserRole.analyst.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    projects: Mapped[List["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


# ─── Domain ──────────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.pending,
        server_default=ProjectStatus.pending.value,
    )
    manager_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    measures: Mapped[List["Measure"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    financial_results: Mapped[List["FinancialResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    ahp_results: Mapped[List["AHPResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    topsis_results: Mapped[List["TopsisResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    eco_results: Mapped[List["EcoResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    scenario_results: Mapped[List["ScenarioResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    comparison_results: Mapped[List["ComparisonResult"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Measure(Base):
    __tablename__ = "measures"
    __table_args__ = (Index("ix_measures_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    measure_type: Mapped[MeasureType] = mapped_column(
        Enum(MeasureType, name="measure_type"), nullable=False
    )
    initial_investment: Mapped[float] = mapped_column(Float, nullable=False)
    operational_cost: Mapped[float] = mapped_column(Float, nullable=False)
    expected_savings: Mapped[float] = mapped_column(Float, nullable=False)
    lifetime_years: Mapped[int] = mapped_column(Integer, nullable=False)
    emission_reduction: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped["Project"] = relationship(back_populates="measures")


# ─── Result tables (JSONB) ───────────────────────────────────────────────────
#
# Each calculator service writes its inputs and outputs to a dedicated
# table. JSONB keeps the result schema flexible; ``version`` allows safe
# evolution of the calculator without migrations.


class _ResultMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed", server_default="completed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FinancialResult(_ResultMixin, Base):
    __tablename__ = "financial_results"
    __table_args__ = (Index("ix_financial_results_project_id", "project_id"),)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="financial_results")


class AHPResult(_ResultMixin, Base):
    __tablename__ = "ahp_results"
    __table_args__ = (Index("ix_ahp_results_project_id", "project_id"),)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="ahp_results")


class TopsisResult(_ResultMixin, Base):
    __tablename__ = "topsis_results"
    __table_args__ = (Index("ix_topsis_results_project_id", "project_id"),)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="topsis_results")


class EcoResult(_ResultMixin, Base):
    __tablename__ = "eco_results"
    __table_args__ = (Index("ix_eco_results_project_id", "project_id"),)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="eco_results")


class ScenarioResult(_ResultMixin, Base):
    __tablename__ = "scenario_results"
    __table_args__ = (Index("ix_scenario_results_project_id", "project_id"),)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="scenario_results")


class ComparisonResult(_ResultMixin, Base):
    __tablename__ = "comparison_results"
    __table_args__ = (
        Index("ix_comparison_results_project_id", "project_id"),
        UniqueConstraint("project_id", "version", name="uq_comparison_project_version"),
    )

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="comparison_results")
