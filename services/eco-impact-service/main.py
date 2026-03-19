from fastapi import FastAPI, Depends
from typing import List
import schemas
import calculator
import auth

app = FastAPI(title="Eco Impact Service", root_path="/api/eco")


@app.get("/health")
def health():
    return {"status": "ok", "service": "eco-impact-service"}


@app.post("/analyze", response_model=schemas.EcoResult)
def analyze_single(
    data: schemas.EcoInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Аналіз екологічного ефекту одного заходу.
    Розраховує зменшення CO2, Carbon Footprint,
    відвернений збиток та вартість тонни CO2
    """
    return calculator.calculate_eco_impact(data)


@app.post("/analyze/portfolio", response_model=schemas.PortfolioEcoResult)
def analyze_portfolio(
    data: schemas.PortfolioEcoInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Аналіз екологічного ефекту портфелю заходів.
    Повертає результати по кожному заходу
    та загальні підсумки
    """
    results = [calculator.calculate_eco_impact(m) for m in data.measures]

    total_co2 = sum(r.co2_reduction_tons_per_year for r in results)
    total_damage = sum(r.averted_damage_uah for r in results)

    return schemas.PortfolioEcoResult(
        results=results,
        total_co2_reduction=round(total_co2, 3),
        total_averted_damage_uah=round(total_damage, 2)
    )


@app.get("/emission-factors")
def get_emission_factors(
    current_user: dict = Depends(auth.get_current_user)
):
    """Повертає всі коефіцієнти емісії CO2"""
    return {
        fuel.value: factor
        for fuel, factor in calculator.EMISSION_FACTORS.items()
    }