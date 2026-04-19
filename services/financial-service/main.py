import os
from typing import List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth
import calculator
import schemas


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Financial Analysis Service",
    root_path="/api/v1/financial",
    docs_url=None if _is_production() else "/docs",
    redoc_url=None if _is_production() else "/redoc",
    openapi_url=None if _is_production() else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


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