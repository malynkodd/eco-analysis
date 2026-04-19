"""Financial analysis service — NPV / IRR / BCR / payback / LCCA."""
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
    {"name": "financial", "description": "Stateless financial calculations."},
    {"name": "projects", "description": "Project-scoped financial results."},
    {"name": "results", "description": "Persisted result lookup."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Financial Analysis Service",
    description="NPV, IRR (brentq), BCR, payback, LCCA per energy-saving measure.",
    root_path="/api/v1/financial",
    openapi_tags=OPENAPI_TAGS,
)


class SavedFinancialResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.FinancialResult


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "financial-service"}


def _analyze(data: schemas.FinancialInput) -> schemas.FinancialResult:
    try:
        return calculator.analyze_measure(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/analyze",
    response_model=schemas.FinancialResult,
    tags=["financial"],
    summary="Analyse a single measure",
)
def analyze_single(
    data: schemas.FinancialInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _analyze(data)


@app.post(
    "/analyze/portfolio",
    response_model=schemas.PortfolioResult,
    tags=["financial"],
    summary="Analyse a portfolio of measures with a shared discount rate",
)
def analyze_portfolio(
    data: schemas.PortfolioInput,
    current_user: dict = Depends(auth.get_current_user),
):
    results = []
    for measure in data.measures:
        measure.discount_rate = data.discount_rate
        results.append(_analyze(measure))
    return schemas.PortfolioResult(results=results)


@app.post(
    "/projects/{project_id}/analyze",
    response_model=SavedFinancialResult,
    tags=["projects"],
    summary="Run + persist a financial analysis for a project",
)
def analyze_and_save(
    project_id: int,
    payload: schemas.FinancialInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _analyze(payload)
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
    tags=["projects"],
    summary="List persisted financial results for a project (paginated)",
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
        SavedFinancialResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.FinancialResult(**r.result_data),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/results/{result_id}",
    response_model=Optional[SavedFinancialResult],
    tags=["results"],
    summary="Fetch a single persisted financial result by id",
)
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
