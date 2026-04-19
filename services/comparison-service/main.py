"""Comparison service — cross-method ranking + Pareto front."""
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


# ─── Stateless ───────────────────────────────────────────────────────────────


@app.post("/compare", response_model=schemas.ComparisonResult)
def compare(
    data: schemas.ComparisonInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return calculator.compare_measures(data.measures)


# ─── Persisted ───────────────────────────────────────────────────────────────


class SavedComparisonResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.ComparisonResult


@app.post(
    "/projects/{project_id}/compare", response_model=SavedComparisonResult
)
def compare_and_save(
    project_id: int,
    payload: schemas.ComparisonInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = calculator.compare_measures(payload.measures)
    row = persistence.save_result(
        db,
        project_id=project_id,
        input_data=payload.model_dump(),
        result_data=result.model_dump(),
    )
    return SavedComparisonResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=result,
    )


@app.get(
    "/projects/{project_id}/results",
    response_model=List[SavedComparisonResult],
)
def list_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_for_project(db, project_id)
    return [
        SavedComparisonResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.ComparisonResult(**r.result_data),
        )
        for r in rows
    ]


@app.get("/results/{result_id}", response_model=Optional[SavedComparisonResult])
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_one(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedComparisonResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=schemas.ComparisonResult(**row.result_data),
    )
