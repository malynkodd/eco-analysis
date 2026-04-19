import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import ahp
import auth
import schemas
import topsis


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Multi-Criteria Service",
    root_path="/api/v1/multicriteria",
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
    return {"status": "ok", "service": "multi-criteria-service"}


@app.post("/ahp", response_model=schemas.AHPResult)
def run_ahp(
    data: schemas.AHPInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Метод AHP (Analytic Hierarchy Process).
    Матриця парних порівнянь за шкалою Сааті (1-9).
    CR має бути < 0.1 для узгодженої матриці.
    """
    n = len(data.criteria)
    if len(data.comparison_matrix) != n:
        raise HTTPException(400, "Розмір матриці не відповідає кількості критеріїв")
    for row in data.comparison_matrix:
        if len(row) != n:
            raise HTTPException(400, "Матриця має бути квадратною")

    return ahp.calculate_ahp(data)


@app.post("/topsis", response_model=schemas.TOPSISResult)
def run_topsis(
    data: schemas.TOPSISInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Метод TOPSIS.
    Ранжує альтернативи за відстанню до ідеального рішення.
    Коефіцієнт близькості: 0 = найгірше, 1 = найкраще.
    """
    if abs(sum(data.weights) - 1.0) > 0.01:
        raise HTTPException(400, "Сума ваг має дорівнювати 1.0")
    if len(data.weights) != len(data.criteria):
        raise HTTPException(400, "Кількість ваг має відповідати кількості критеріїв")

    return topsis.calculate_topsis(data)


@app.post("/combined", response_model=schemas.CombinedResult)
def run_combined(
    data: schemas.CombinedInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Комбінований аналіз: спочатку AHP визначає ваги,
    потім TOPSIS ранжує альтернативи з цими вагами.
    """
    # Крок 1: AHP — отримуємо ваги критеріїв
    ahp_input = schemas.AHPInput(
        criteria=data.criteria,
        comparison_matrix=data.comparison_matrix,
        alternatives=data.alternatives
    )
    ahp_result = ahp.calculate_ahp(ahp_input)

    if not ahp_result.is_consistent:
        raise HTTPException(
            400,
            f"Матриця AHP неузгоджена (CR={ahp_result.consistency_ratio}). "
            f"CR має бути < 0.1. Перегляньте парні порівняння."
        )

    # Крок 2: TOPSIS — ранжуємо з вагами від AHP
    topsis_input = schemas.TOPSISInput(
        criteria=data.criteria,
        weights=ahp_result.weights,
        is_benefit=data.is_benefit,
        alternatives=data.alternatives
    )
    topsis_result = topsis.calculate_topsis(topsis_input)

    return schemas.CombinedResult(
        ahp=ahp_result,
        topsis=topsis_result
    )