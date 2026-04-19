"""Financial analysis service."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import calculator
import persistence
import schemas
from db.base import get_db


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


# ─── Stateless analysis ──────────────────────────────────────────────────────


@app.post("/analyze", response_model=schemas.FinancialResult)
def analyze_single(
    data: schemas.FinancialInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return calculator.analyze_measure(data)


@app.post("/analyze/portfolio", response_model=schemas.PortfolioResult)
def analyze_portfolio(
    data: schemas.PortfolioInput,
    current_user: dict = Depends(auth.get_current_user),
):
    results = []
    for measure in data.measures:
        measure.discount_rate = data.discount_rate
        results.append(calculator.analyze_measure(measure))
    return schemas.PortfolioResult(results=results)


# ─── Persisted analysis ──────────────────────────────────────────────────────


class SaveAnalysisRequest(BaseModel):
    project_id: int
    input: schemas.FinancialInput


class SavedFinancialResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.FinancialResult


@app.post("/projects/{project_id}/analyze", response_model=SavedFinancialResult)
def analyze_and_save(
    project_id: int,
    payload: schemas.FinancialInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = calculator.analyze_measure(payload)
    row = persistence.save_result(
        db,
        project_id=project_id,
        input_data=payload.model_dump(),
        result_data=result.model_dump(),
    )
    return SavedFinancialResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=result,
    )


@app.get(
    "/projects/{project_id}/results",
    response_model=List[SavedFinancialResult],
)
def list_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_for_project(db, project_id)
    return [
        SavedFinancialResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.FinancialResult(**r.result_data),
        )
        for r in rows
    ]


@app.get("/results/{result_id}", response_model=Optional[SavedFinancialResult])
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_one(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedFinancialResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=schemas.FinancialResult(**row.result_data),
    )
