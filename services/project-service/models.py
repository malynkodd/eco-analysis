from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import enum


class MeasureType(str, enum.Enum):
    insulation = "insulation"            # утеплення
    equipment = "equipment"              # заміна обладнання
    treatment = "treatment"              # очисні споруди
    renewable = "renewable"              # відновлювана енергетика


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_username = Column(String, nullable=False)
    # Статус затвердження: "pending" | "approved" | "rejected"
    status = Column(String, nullable=False, default="pending")
    # Коментар менеджера при затвердженні/відхиленні
    manager_comment = Column(Text, nullable=True)

    # Зв'язок з заходами
    measures = relationship("Measure", back_populates="project",
                            cascade="all, delete-orphan")


class Measure(Base):
    __tablename__ = "measures"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String, nullable=False)
    measure_type = Column(Enum(MeasureType), nullable=False)

    # Фінансові параметри (з ТЗ)
    initial_investment = Column(Float, nullable=False)   # початкові інвестиції
    operational_cost = Column(Float, nullable=False)     # операційні витрати/рік
    expected_savings = Column(Float, nullable=False)     # очікувана економія/рік
    lifetime_years = Column(Integer, nullable=False)     # термін експлуатації

    # Екологічний параметр (з ТЗ)
    emission_reduction = Column(Float, nullable=False)   # зменшення викидів т/рік

    # Зв'язок з проєктом
    project = relationship("Project", back_populates="measures")