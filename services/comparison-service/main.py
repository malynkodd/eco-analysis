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
    title="Comparison Service",
    root_path="/api/v1/comparison",
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
    return {"status": "ok", "service": "comparison-service"}


@app.post("/compare", response_model=schemas.ComparisonResult)
def compare(
    data: schemas.ComparisonInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Порівняльний аналіз заходів за всіма методами.
    Будує зведену таблицю рангів, консенсусний рейтинг
    та Pareto-фронт (NPV vs CO2).
    """
    return calculator.compare_measures(data.measures)