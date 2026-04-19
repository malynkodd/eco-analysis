"""Multi-criteria service — AHP + TOPSIS."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

import ahp
import auth
import persistence
import schemas
import topsis
from db.base import get_db


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


def _validate_ahp(data: schemas.AHPInput) -> None:
    n = len(data.criteria)
    if len(data.comparison_matrix) != n:
        raise HTTPException(400, "Matrix size does not match number of criteria")
    for row in data.comparison_matrix:
        if len(row) != n:
            raise HTTPException(400, "Comparison matrix must be square")


def _validate_topsis(data: schemas.TOPSISInput) -> None:
    if abs(sum(data.weights) - 1.0) > 0.01:
        raise HTTPException(400, "Weights must sum to 1.0")
    if len(data.weights) != len(data.criteria):
        raise HTTPException(
            400, "Number of weights must match number of criteria"
        )


# ─── Stateless ───────────────────────────────────────────────────────────────


@app.post("/ahp", response_model=schemas.AHPResult)
def run_ahp(
    data: schemas.AHPInput, current_user: dict = Depends(auth.get_current_user)
):
    _validate_ahp(data)
    return ahp.calculate_ahp(data)


@app.post("/topsis", response_model=schemas.TOPSISResult)
def run_topsis(
    data: schemas.TOPSISInput, current_user: dict = Depends(auth.get_current_user)
):
    _validate_topsis(data)
    return topsis.calculate_topsis(data)


@app.post("/combined", response_model=schemas.CombinedResult)
def run_combined(
    data: schemas.CombinedInput,
    current_user: dict = Depends(auth.get_current_user),
):
    ahp_input = schemas.AHPInput(
        criteria=data.criteria,
        comparison_matrix=data.comparison_matrix,
        alternatives=data.alternatives,
    )
    _validate_ahp(ahp_input)
    ahp_result = ahp.calculate_ahp(ahp_input)
    if not ahp_result.is_consistent:
        raise HTTPException(
            400,
            f"AHP matrix is inconsistent (CR={ahp_result.consistency_ratio}). "
            "CR must be < 0.1.",
        )
    topsis_input = schemas.TOPSISInput(
        criteria=data.criteria,
        weights=ahp_result.weights,
        is_benefit=data.is_benefit,
        alternatives=data.alternatives,
    )
    return schemas.CombinedResult(
        ahp=ahp_result, topsis=topsis.calculate_topsis(topsis_input)
    )


# ─── Persisted ───────────────────────────────────────────────────────────────


class SavedAHPResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.AHPResult


class SavedTopsisResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.TOPSISResult


@app.post("/projects/{project_id}/ahp", response_model=SavedAHPResult)
def ahp_and_save(
    project_id: int,
    payload: schemas.AHPInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    _validate_ahp(payload)
    result = ahp.calculate_ahp(payload)
    row = persistence.save_ahp(
        db,
        project_id=project_id,
        input_data=payload.model_dump(),
        result_data=result.model_dump(),
    )
    return SavedAHPResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=result,
    )


@app.post("/projects/{project_id}/topsis", response_model=SavedTopsisResult)
def topsis_and_save(
    project_id: int,
    payload: schemas.TOPSISInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    _validate_topsis(payload)
    result = topsis.calculate_topsis(payload)
    row = persistence.save_topsis(
        db,
        project_id=project_id,
        input_data=payload.model_dump(),
        result_data=result.model_dump(),
    )
    return SavedTopsisResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=result,
    )


@app.get(
    "/projects/{project_id}/ahp/results", response_model=List[SavedAHPResult]
)
def list_ahp_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_ahp(db, project_id)
    return [
        SavedAHPResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.AHPResult(**r.result_data),
        )
        for r in rows
    ]


@app.get(
    "/projects/{project_id}/topsis/results",
    response_model=List[SavedTopsisResult],
)
def list_topsis_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_topsis(db, project_id)
    return [
        SavedTopsisResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.TOPSISResult(**r.result_data),
        )
        for r in rows
    ]


@app.get("/results/ahp/{result_id}", response_model=Optional[SavedAHPResult])
def get_ahp_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_ahp(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedAHPResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=schemas.AHPResult(**row.result_data),
    )


@app.get(
    "/results/topsis/{result_id}", response_model=Optional[SavedTopsisResult]
)
def get_topsis_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_topsis(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedTopsisResult(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,
        result=schemas.TOPSISResult(**row.result_data),
    )
