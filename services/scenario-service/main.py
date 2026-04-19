"""Scenario service — what-if, sensitivity, break-even analyses."""

from __future__ import annotations

from typing import Any, List, Optional

import auth
import calculator
import persistence
import schemas
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from eco_common.api_setup import create_app
from eco_common.envelope import paginate

OPENAPI_TAGS = [
    {"name": "scenario", "description": "Stateless what-if / sensitivity / break-even."},
    {"name": "projects", "description": "Project-scoped scenarios."},
    {"name": "results", "description": "Persisted scenario lookup."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Scenario Service",
    description="What-if, sensitivity (tornado), break-even analyses around NPV.",
    root_path="/api/v1/scenario",
    openapi_tags=OPENAPI_TAGS,
)


class SavedScenarioResult(BaseModel):
    id: int
    project_id: int
    kind: str
    version: int
    status: str
    result: Any


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "scenario-service"}


def _guarded(callable_, payload):
    try:
        return callable_(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _persist(
    db: Session,
    project_id: int,
    kind: str,
    payload_dict: dict,
    result_dict: Any,
) -> persistence.ScenarioResult:
    return persistence.save_result(
        db,
        project_id=project_id,
        input_data={"kind": kind, "payload": payload_dict},
        result_data={"kind": kind, "result": result_dict},
    )


@app.post(
    "/whatif",
    response_model=List[schemas.WhatIfResult],
    tags=["scenario"],
    summary="What-if analysis: NPV change for each parameter override",
)
def whatif_analysis(
    data: schemas.WhatIfInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_whatif, data)


@app.post(
    "/sensitivity",
    response_model=schemas.SensitivityAnalysisResult,
    tags=["scenario"],
    summary="Sensitivity (tornado) analysis around the base scenario",
)
def sensitivity_analysis(
    data: schemas.SensitivityInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_sensitivity, data)


@app.post(
    "/breakeven",
    response_model=schemas.BreakEvenResult,
    tags=["scenario"],
    summary="Break-even analysis: thresholds where NPV = 0",
)
def breakeven_analysis(
    data: schemas.BreakEvenInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_breakeven, data)


@app.post(
    "/projects/{project_id}/whatif",
    response_model=SavedScenarioResult,
    tags=["projects"],
    summary="Run + persist a what-if analysis for a project",
)
def whatif_and_save(
    project_id: int,
    payload: schemas.WhatIfInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_whatif, payload)
    result_payload = [r.model_dump() for r in result]
    row = _persist(db, project_id, "whatif", payload.model_dump(), result_payload)
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="whatif",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.post(
    "/projects/{project_id}/sensitivity",
    response_model=SavedScenarioResult,
    tags=["projects"],
    summary="Run + persist a sensitivity analysis for a project",
)
def sensitivity_and_save(
    project_id: int,
    payload: schemas.SensitivityInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_sensitivity, payload)
    result_payload = result.model_dump()
    row = _persist(db, project_id, "sensitivity", payload.model_dump(), result_payload)
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="sensitivity",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.post(
    "/projects/{project_id}/breakeven",
    response_model=SavedScenarioResult,
    tags=["projects"],
    summary="Run + persist a break-even analysis for a project",
)
def breakeven_and_save(
    project_id: int,
    payload: schemas.BreakEvenInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_breakeven, payload)
    result_payload = result.model_dump()
    row = _persist(db, project_id, "breakeven", payload.model_dump(), result_payload)
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="breakeven",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.get(
    "/projects/{project_id}/results",
    tags=["projects"],
    summary="List persisted scenarios for a project (paginated)",
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
        SavedScenarioResult(
            id=r.id,
            project_id=r.project_id,
            kind=r.result_data.get("kind", "unknown"),
            version=r.version,
            status=r.status,
            result=r.result_data.get("result"),
        )
        for r in sliced
    ]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/results/{result_id}",
    response_model=Optional[SavedScenarioResult],
    tags=["results"],
    summary="Fetch a single persisted scenario by id",
)
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    row = persistence.get_one(db, result_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind=row.result_data.get("kind", "unknown"),
        version=row.version,
        status=row.status,
        result=row.result_data.get("result"),
    )
