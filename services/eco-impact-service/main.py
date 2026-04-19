"""Eco-impact service — CO2/footprint/damage calculations."""
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
    title="Eco Impact Service",
    root_path="/api/v1/eco",
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
    return {"status": "ok", "service": "eco-impact-service"}


# ─── Stateless analysis ──────────────────────────────────────────────────────


@app.post("/analyze", response_model=schemas.EcoResult)
def analyze_single(
    data: schemas.EcoInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return calculator.calculate_eco_impact(data)


@app.post("/analyze/portfolio", response_model=schemas.PortfolioEcoResult)
def analyze_portfolio(
    data: schemas.PortfolioEcoInput,
    current_user: dict = Depends(auth.get_current_user),
):
    results = [calculator.calculate_eco_impact(m) for m in data.measures]
    total_co2 = sum(r.co2_reduction_tons_per_year for r in results)
    total_damage = sum(r.averted_damage_uah for r in results)
    return schemas.PortfolioEcoResult(
        results=results,
        total_co2_reduction=round(total_co2, 3),
        total_averted_damage_uah=round(total_damage, 2),
    )


@app.get("/emission-factors")
def get_emission_factors(current_user: dict = Depends(auth.get_current_user)):
    return {fuel.value: factor for fuel, factor in calculator.EMISSION_FACTORS.items()}


# ─── Persisted analysis ──────────────────────────────────────────────────────


class SavedEcoResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.EcoResult


@app.post("/projects/{project_id}/analyze", response_model=SavedEcoResult)
def analyze_and_save(
    project_id: int,
    payload: schemas.EcoInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = calculator.calculate_eco_impact(payload)
    row = persistence.save_result(
        db,
        project_id=project_id,
        input_data=payload.model_dump(),
        result_data=result.model_dump(),
    )
    return SavedEcoResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=result,
    )


@app.get("/projects/{project_id}/results", response_model=List[SavedEcoResult])
def list_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_for_project(db, project_id)
    return [
        SavedEcoResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.EcoResult(**r.result_data),
        )
        for r in rows
    ]


@app.get("/results/{result_id}", response_model=Optional[SavedEcoResult])
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_one(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedEcoResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=schemas.EcoResult(**row.result_data),
    )
