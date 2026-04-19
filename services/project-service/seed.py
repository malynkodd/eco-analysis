"""Optional dev seed: load two demo projects owned by the bootstrapped admin.

Skipped when (a) no admin user exists yet, or (b) any project already
exists. Run manually as ``python seed.py`` from the project-service container.
"""
from __future__ import annotations

from db.base import SessionLocal
from db.models import Measure, MeasureType, Project, ProjectStatus, User, UserRole


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Project).count() > 0:
            print("Seed data already exists, skipping.")
            return

        admin = db.query(User).filter(User.role == UserRole.admin).first()
        if not admin:
            print("No admin user found — cannot seed. Skipping.")
            return

        p1 = Project(
            name="School #15 — energy efficiency",
            description="Bundle of measures to improve school energy efficiency",
            owner_id=admin.id,
            status=ProjectStatus.pending,
        )
        db.add(p1)
        db.flush()

        for m in (
            Measure(
                project_id=p1.id,
                name="Facade insulation",
                measure_type=MeasureType.insulation,
                initial_investment=500_000,
                operational_cost=5_000,
                expected_savings=80_000,
                lifetime_years=20,
                emission_reduction=45.5,
            ),
            Measure(
                project_id=p1.id,
                name="Boiler replacement",
                measure_type=MeasureType.equipment,
                initial_investment=350_000,
                operational_cost=12_000,
                expected_savings=95_000,
                lifetime_years=15,
                emission_reduction=78.2,
            ),
            Measure(
                project_id=p1.id,
                name="Solar panels",
                measure_type=MeasureType.renewable,
                initial_investment=420_000,
                operational_cost=3_000,
                expected_savings=65_000,
                lifetime_years=25,
                emission_reduction=62.1,
            ),
        ):
            db.add(m)

        p2 = Project(
            name="Plant — wastewater treatment",
            description="Modernization of wastewater treatment system",
            owner_id=admin.id,
            status=ProjectStatus.pending,
        )
        db.add(p2)
        db.flush()
        for m in (
            Measure(
                project_id=p2.id,
                name="Biological treatment",
                measure_type=MeasureType.treatment,
                initial_investment=1_200_000,
                operational_cost=45_000,
                expected_savings=180_000,
                lifetime_years=20,
                emission_reduction=120.0,
            ),
            Measure(
                project_id=p2.id,
                name="Filtration system",
                measure_type=MeasureType.treatment,
                initial_investment=800_000,
                operational_cost=25_000,
                expected_savings=110_000,
                lifetime_years=15,
                emission_reduction=85.0,
            ),
        ):
            db.add(m)

        db.commit()
        print(f"Seeded 2 projects owned by admin '{admin.username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
