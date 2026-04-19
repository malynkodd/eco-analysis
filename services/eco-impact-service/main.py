"""Eco-impact service — CO2/footprint/damage calculations."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import auth
import calculator
import persistence
import schemas
from db.base import get_db
from eco_common.api_setup import create_app
from eco_common.envelope import paginate

OPENAPI_TAGS = [
    {"name": "eco", "description": "Stateless eco-impact calculations."},
    {"name": "projects", "description": "Project-scoped eco results."},
    {"name": "results", "description": "Persisted result lookup."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Eco Impact Service",
    description="CO2 reduction, averted damage, emission factors.",
    root_path="/api/v1/eco",
    openapi_tags=OPENAPI_TAGS,
)


class SavedEcoResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.EcoResult


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "eco-impact-service"}


@app.post(
    "/analyze",
    response_model=schemas.EcoResult,
    tags=["eco"],
    summary="Compute CO2 reduction + averted damage for a single measure",
)
def analyze_single(
    data: schemas.EcoInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return calculator.calculate_eco_impact(data)


@app.post(
    "/analyze/portfolio",
    response_model=schemas.PortfolioEcoResult,
    tags=["eco"],
    summary="Aggregate eco-impact for a portfolio of measures",
)
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


@app.get(
    "/emission-factors",
    tags=["eco"],
    summary="Return the emission-factor table used by the calculator",
)
def get_emission_factors(current_user: dict = Depends(auth.get_current_user)):
    return {fuel.value: factor for fuel, factor in calculator.EMISSION_FACTORS.items()}


@app.post(
    "/projects/{project_id}/analyze",
    response_model=SavedEcoResult,
    tags=["projects"],
    summary="Run + persist an eco analysis for a project",
)
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


@app.get(
    "/projects/{project_id}/results",
    tags=["projects"],
    summary="List persisted eco results for a project (paginated)",
)
def list_results(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_for_project(db, project_id)
    total = len(rows)
    sliced = rows[(page - 1) * limit : (page - 1) * limit + limit]
    items = [
        SavedEcoResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.EcoResult(**r.result_data),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/results/{result_id}",
    response_model=Optional[SavedEcoResult],
    tags=["results"],
    summary="Fetch a single persisted eco result by id",
)
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
