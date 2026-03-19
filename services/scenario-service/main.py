from fastapi import FastAPI, Depends
from typing import List
import schemas
import calculator
import auth

app = FastAPI(title="Scenario Service", root_path="/api/scenario")


@app.get("/health")
def health():
    return {"status": "ok", "service": "scenario-service"}


@app.post("/whatif", response_model=List[schemas.WhatIfResult])
def whatif_analysis(
    data: schemas.WhatIfInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    What-if аналіз: показує як зміна параметрів впливає на NPV.
    Можна змінювати: initial_investment, operational_cost,
    expected_savings, lifetime_years, discount_rate
    """
    return calculator.run_whatif(data)


@app.post("/sensitivity", response_model=schemas.SensitivityAnalysisResult)
def sensitivity_analysis(
    data: schemas.SensitivityInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Sensitivity Analysis (аналіз чутливості).
    Варіює кожен параметр на ±variation_percent%.
    Результати відсортовані за впливом на NPV (дані для Tornado chart).
    """
    return calculator.run_sensitivity(data)


@app.post("/breakeven", response_model=schemas.BreakEvenResult)
def breakeven_analysis(
    data: schemas.BreakEvenInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Break-even аналіз: знаходить порогові значення при яких NPV = 0.
    - Мінімальна економія
    - Максимальна інвестиція
    - Максимальна ставка дисконтування (= IRR)
    - Мінімальний термін окупності
    """
    return calculator.run_breakeven(data)