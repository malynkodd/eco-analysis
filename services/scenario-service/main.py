"""Scenario service — what-if, sensitivity, break-even analyses."""
from __future__ import annotations

import os
from typing import Any, List, Optional

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
    title="Scenario Service",
    root_path="/api/v1/scenario",
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
    return {"status": "ok", "service": "scenario-service"}


# ─── Stateless ───────────────────────────────────────────────────────────────


def _guarded(callable_, payload):
    try:
        return callable_(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/whatif", response_model=List[schemas.WhatIfResult])
def whatif_analysis(
    data: schemas.WhatIfInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_whatif, data)


@app.post("/sensitivity", response_model=schemas.SensitivityAnalysisResult)
def sensitivity_analysis(
    data: schemas.SensitivityInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_sensitivity, data)


@app.post("/breakeven", response_model=schemas.BreakEvenResult)
def breakeven_analysis(
    data: schemas.BreakEvenInput,
    current_user: dict = Depends(auth.get_current_user),
):
    return _guarded(calculator.run_breakeven, data)


# ─── Persisted ───────────────────────────────────────────────────────────────


class SavedScenarioResult(BaseModel):
    id: int
    project_id: int
    kind: str
    version: int
    status: str
    result: Any


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
    "/projects/{project_id}/whatif", response_model=SavedScenarioResult
)
def whatif_and_save(
    project_id: int,
    payload: schemas.WhatIfInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_whatif, payload)
    result_payload = [r.model_dump() for r in result]
    row = _persist(
        db, project_id, "whatif", payload.model_dump(), result_payload
    )
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="whatif",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.post(
    "/projects/{project_id}/sensitivity", response_model=SavedScenarioResult
)
def sensitivity_and_save(
    project_id: int,
    payload: schemas.SensitivityInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_sensitivity, payload)
    result_payload = result.model_dump()
    row = _persist(
        db, project_id, "sensitivity", payload.model_dump(), result_payload
    )
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="sensitivity",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.post(
    "/projects/{project_id}/breakeven", response_model=SavedScenarioResult
)
def breakeven_and_save(
    project_id: int,
    payload: schemas.BreakEvenInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    result = _guarded(calculator.run_breakeven, payload)
    result_payload = result.model_dump()
    row = _persist(
        db, project_id, "breakeven", payload.model_dump(), result_payload
    )
    return SavedScenarioResult(
        id=row.id,
        project_id=row.project_id,
        kind="breakeven",
        version=row.version,
        status=row.status,
        result=result_payload,
    )


@app.get(
    "/projects/{project_id}/results", response_model=List[SavedScenarioResult]
)
def list_results(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    rows = persistence.list_for_project(db, project_id)
    return [
        SavedScenarioResult(
            id=r.id,
            project_id=r.project_id,
            kind=r.result_data.get("kind", "unknown"),
            version=r.version,
            status=r.status,
            result=r.result_data.get("result"),
        )
        for r in rows
    ]


@app.get("/results/{result_id}", response_model=Optional[SavedScenarioResult])
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
