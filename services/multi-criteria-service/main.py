"""Multi-criteria service — AHP + TOPSIS."""

from __future__ import annotations

from typing import Optional

import ahp
import auth
import persistence
import schemas
import topsis
from ahp import AHPValidationError
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from topsis import TOPSISValidationError

from db.base import get_db
from eco_common.api_setup import create_app
from eco_common.envelope import paginate

OPENAPI_TAGS = [
    {"name": "ahp", "description": "Analytical Hierarchy Process."},
    {"name": "topsis", "description": "TOPSIS distance-to-ideal ranking."},
    {"name": "combined", "description": "AHP weights feeding TOPSIS."},
    {"name": "projects", "description": "Project-scoped results."},
    {"name": "results", "description": "Persisted result lookup."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Multi-Criteria Service",
    description="AHP (eigenvector) + TOPSIS for ranking energy-saving alternatives.",
    root_path="/api/v1/multicriteria",
    openapi_tags=OPENAPI_TAGS,
)


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


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "multi-criteria-service"}


def _run_ahp(data: schemas.AHPInput) -> schemas.AHPResult:
    try:
        return ahp.calculate_ahp(data)
    except AHPValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _run_topsis(data: schemas.TOPSISInput) -> schemas.TOPSISResult:
    try:
        return topsis.calculate_topsis(data)
    except TOPSISValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/ahp",
    response_model=schemas.AHPResult,
    tags=["ahp"],
    summary="Run AHP and return weights, CR, ranking",
)
def run_ahp(data: schemas.AHPInput, current_user: dict = Depends(auth.get_current_user)):
    return _run_ahp(data)


@app.post(
    "/topsis",
    response_model=schemas.TOPSISResult,
    tags=["topsis"],
    summary="Run TOPSIS with caller-supplied weights",
)
def run_topsis(data: schemas.TOPSISInput, current_user: dict = Depends(auth.get_current_user)):
    return _run_topsis(data)


@app.post(
    "/combined",
    response_model=schemas.CombinedResult,
    tags=["combined"],
    summary="AHP + TOPSIS in one call (weights flow from AHP into TOPSIS)",
)
def run_combined(
    data: schemas.CombinedInput,
    current_user: dict = Depends(auth.get_current_user),
):
    ahp_input = schemas.AHPInput(
        criteria=data.criteria,
        comparison_matrix=data.comparison_matrix,
        alternatives=data.alternatives,
        is_benefit=data.is_benefit,
    )
    ahp_result = _run_ahp(ahp_input)
    if not ahp_result.is_consistent:
        raise HTTPException(
            status_code=422,
            detail=(
                f"AHP matrix is inconsistent (CR={ahp_result.consistency_ratio:.4f}); "
                "CR must be < 0.1"
            ),
        )
    topsis_input = schemas.TOPSISInput(
        criteria=data.criteria,
        weights=ahp_result.weights,
        is_benefit=data.is_benefit,
        alternatives=data.alternatives,
    )
    return schemas.CombinedResult(ahp=ahp_result, topsis=_run_topsis(topsis_input))


@app.post(
    "/projects/{project_id}/ahp",
    response_model=SavedAHPResult,
    tags=["projects"],
    summary="Run + persist an AHP result for a project",
)
def ahp_and_save(
    project_id: int,
    payload: schemas.AHPInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _run_ahp(payload)
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


@app.post(
    "/projects/{project_id}/topsis",
    response_model=SavedTopsisResult,
    tags=["projects"],
    summary="Run + persist a TOPSIS result for a project",
)
def topsis_and_save(
    project_id: int,
    payload: schemas.TOPSISInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _run_topsis(payload)
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
    "/projects/{project_id}/ahp/results",
    tags=["projects"],
    summary="List persisted AHP results for a project (paginated)",
)
def list_ahp_results(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_ahp(db, project_id)
    total = len(rows)
    sliced = rows[(page - 1) * limit : (page - 1) * limit + limit]
    items = [
        SavedAHPResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.AHPResult(**r.result_data),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/projects/{project_id}/topsis/results",
    tags=["projects"],
    summary="List persisted TOPSIS results for a project (paginated)",
)
def list_topsis_results(
    project_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_topsis(db, project_id)
    total = len(rows)
    sliced = rows[(page - 1) * limit : (page - 1) * limit + limit]
    items = [
        SavedTopsisResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.TOPSISResult(**r.result_data),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/results/ahp/{result_id}",
    response_model=Optional[SavedAHPResult],
    tags=["results"],
    summary="Fetch a single persisted AHP result by id",
)
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
    "/results/topsis/{result_id}",
    response_model=Optional[SavedTopsisResult],
    tags=["results"],
    summary="Fetch a single persisted TOPSIS result by id",
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
