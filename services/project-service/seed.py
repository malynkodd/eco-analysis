import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Project, Measure, MeasureType
import sys
sys.path.insert(0, '/app')

DATABASE_URL = os.getenv("DATABASE_URL")


def seed():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Перевіряємо чи вже є дані
    if db.query(Project).count() > 0:
        print("✅ Seed data already exists, skipping...")
        db.close()
        return

    print("🌱 Seeding test data...")

    # Тестовий проєкт 1
    p1 = Project(
        name="Школа №15 — Енергоефективність",
        description="Комплекс заходів з підвищення енергоефективності школи",
        owner_username="admin"
    )
    db.add(p1)
    db.flush()

    measures1 = [
        Measure(
            project_id=p1.id, name="Утеплення фасаду",
            measure_type=MeasureType.insulation,
            initial_investment=500000, operational_cost=5000,
            expected_savings=80000, lifetime_years=20,
            emission_reduction=45.5
        ),
        Measure(
            project_id=p1.id, name="Заміна котельні",
            measure_type=MeasureType.equipment,
            initial_investment=350000, operational_cost=12000,
            expected_savings=95000, lifetime_years=15,
            emission_reduction=78.2
        ),
        Measure(
            project_id=p1.id, name="Сонячні панелі",
            measure_type=MeasureType.renewable,
            initial_investment=420000, operational_cost=3000,
            expected_savings=65000, lifetime_years=25,
            emission_reduction=62.1
        ),
    ]
    for m in measures1:
        db.add(m)

    # Тестовий проєкт 2
    p2 = Project(
        name="Завод — Очистка стічних вод",
        description="Модернізація системи очистки стічних вод",
        owner_username="admin"
    )
    db.add(p2)
    db.flush()

    measures2 = [
        Measure(
            project_id=p2.id, name="Біологічна очистка",
            measure_type=MeasureType.treatment,
            initial_investment=1200000, operational_cost=45000,
            expected_savings=180000, lifetime_years=20,
            emission_reduction=120.0
        ),
        Measure(
            project_id=p2.id, name="Фільтраційна система",
            measure_type=MeasureType.treatment,
            initial_investment=800000, operational_cost=25000,
            expected_savings=110000, lifetime_years=15,
            emission_reduction=85.0
        ),
    ]
    for m in measures2:
        db.add(m)

    db.commit()
    print("✅ Seed data created successfully!")
    print(f"   - Project: {p1.name} ({len(measures1)} measures)")
    print(f"   - Project: {p2.name} ({len(measures2)} measures)")
    db.close()


if __name__ == "__main__":
    seed()