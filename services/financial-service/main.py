from fastapi import FastAPI, Depends
from typing import List
import schemas
import calculator
import auth

app = FastAPI(title="Financial Analysis Service", root_path="/api/financial")


@app.get("/health")
def health():
    return {"status": "ok", "service": "financial-service"}


@app.post("/analyze", response_model=schemas.FinancialResult)
def analyze_single(
    data: schemas.FinancialInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Аналіз одного заходу.
    Розраховує NPV, IRR, BCR, Payback Period, LCCA
    """
    return calculator.analyze_measure(data)


@app.post("/analyze/portfolio", response_model=schemas.PortfolioResult)
def analyze_portfolio(
    data: schemas.PortfolioInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Аналіз портфелю заходів.
    Застосовує одну ставку дисконтування до всіх заходів
    """
    results = []
    for measure in data.measures:
        measure.discount_rate = data.discount_rate
        results.append(calculator.analyze_measure(measure))

    return schemas.PortfolioResult(results=results)