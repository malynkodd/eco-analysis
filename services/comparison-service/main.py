"""Comparison service — cross-method ranking + Pareto front."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import aggregator
import auth
import calculator
import persistence
import schemas
from db.base import get_db
from eco_common.api_setup import create_app
from eco_common.envelope import paginate
from eco_common.exceptions import InternalServiceError
from eco_common.internal import InternalAPI

OPENAPI_TAGS = [
    {"name": "comparison", "description": "Stateless cross-method comparison."},
    {"name": "projects", "description": "Project-scoped comparison + persistence."},
    {"name": "results", "description": "Persisted comparison lookup."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Comparison Service",
    description="Cross-method consensus ranking + Pareto front across measures.",
    root_path="/api/v1/comparison",
    openapi_tags=OPENAPI_TAGS,
)


class SavedComparisonResult(BaseModel):
    id: int
    project_id: int
    version: int
    status: str
    result: schemas.ComparisonResult


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "comparison-service"}


@app.post(
    "/compare",
    response_model=schemas.ComparisonResult,
    tags=["comparison"],
    summary="Compare a list of measures supplied in the request body",
)
def compare(
    data: schemas.ComparisonInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return calculator.compare_measures(data.measures)


@app.post(
    "/projects/{project_id}/compare",
    response_model=SavedComparisonResult,
    tags=["projects"],
    summary="Build measures from sibling services + persist a comparison",
)
async def compare_and_save(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    api = InternalAPI()
    token = current_user["token"]
    try:
        await api.get_project(project_id, token)
        financial = await api.get_financial_results(project_id, token)
        eco = await api.get_eco_results(project_id, token)
        ahp = await api.get_ahp_results(project_id, token)
        topsis = await api.get_topsis_results(project_id, token)
    except InternalServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    measures = aggregator.build_measures(
        financial_results=financial,
        eco_results=eco,
        ahp_results=ahp,
        topsis_results=topsis,
    )
    if not measures:
        raise HTTPException(
            status_code=422,
            detail=(
                "No measures with both financial and eco results found "
                "for this project."
            ),
        )

    result = calculator.compare_measures(measures)
    input_snapshot = {
        "project_id": project_id,
        "measures": [m.model_dump() for m in measures],
    }
    row = persistence.save_result(
        db,
        project_id=project_id,
        input_data=input_snapshot,
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
    tags=["projects"],
    summary="List persisted comparisons for a project (paginated)",
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
        SavedComparisonResult(
            id=r.id,
            project_id=r.project_id,
            version=r.version,
            status=r.status,
            result=schemas.ComparisonResult(**r.result_data),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/results/{result_id}",
    response_model=Optional[SavedComparisonResult],
    tags=["results"],
    summary="Fetch a single persisted comparison by id",
)
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
