"""Project service — CRUD for projects and measures.

Authorization model:
  * analyst — owns the projects they create; can manage their own.
  * manager — read-only on projects; can approve/reject.
  * admin   — full access to every project.
"""

from __future__ import annotations

import asyncio
import logging

import auth
import models
import schemas
from database import get_db
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from eco_common.api_setup import create_app
from eco_common.envelope import paginate
from eco_common.exceptions import CircuitBreakerOpen, RemoteServiceError
from eco_common.internal import InternalAPI

logger = logging.getLogger(__name__)

# IPCC kg CO2 per fuel unit — mirrors eco-impact-service so we can convert
# the project's stored emission_reduction (tons CO2/year) back into the
# units the eco service expects without an extra round-trip.
_FUEL_FACTORS = {
    "natural_gas": 2.04,
    "electricity": 0.37,
    "coal": 2.86,
    "diesel": 2.68,
    "heating_oil": 3.15,
}

OPENAPI_TAGS = [
    {"name": "projects", "description": "Project lifecycle and approval."},
    {"name": "measures", "description": "Energy-efficiency measures attached to a project."},
    {"name": "analysis", "description": "Orchestrated multi-service analysis."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Project Service",
    description="Projects, measures, manager approval workflow.",
    root_path="/api/v1/projects",
    openapi_tags=OPENAPI_TAGS,
)


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "project-service"}


def _require_user_id(current_user: dict) -> int:
    uid = current_user.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="Token missing user id")
    return int(uid)


def _is_privileged(role: str) -> bool:
    return role in ("manager", "admin")


@app.post(
    "/",
    response_model=schemas.ProjectResponse,
    status_code=201,
    tags=["projects"],
    summary="Create a project",
)
def create_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot create projects")
    project = models.Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=_require_user_id(current_user),
        status=models.ProjectStatus.pending,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get(
    "/",
    tags=["projects"],
    summary="List projects (paginated)",
)
def get_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    q = db.query(models.Project)
    if not _is_privileged(current_user["role"]):
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    total = q.count()
    rows = q.order_by(models.Project.id.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [schemas.ProjectResponse.model_validate(r, from_attributes=True) for r in rows]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.get(
    "/{project_id}",
    response_model=schemas.ProjectResponse,
    tags=["projects"],
    summary="Get a single project",
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if not _is_privileged(current_user["role"]):
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch(
    "/{project_id}",
    response_model=schemas.ProjectResponse,
    tags=["projects"],
    summary="Update a project's name or description",
)
def update_project(
    project_id: int,
    update_data: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot edit projects")
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] != "admin":
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    payload = update_data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@app.get(
    "/{project_id}/alternatives",
    response_model=list[schemas.MeasureResponse],
    tags=["measures"],
    summary="List a project's portfolio of alternatives (measures)",
)
def list_alternatives(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if not _is_privileged(current_user["role"]):
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(project.measures)


@app.delete("/{project_id}", tags=["projects"], summary="Delete a project")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot delete projects")
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] != "admin":
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@app.patch(
    "/{project_id}/status",
    response_model=schemas.ProjectResponse,
    tags=["projects"],
    summary="Override project status (manager / admin)",
)
def update_project_status(
    project_id: int,
    status_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(status_code=403, detail="Only managers or admins can change status")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus(status_data.status)
    if status_data.manager_comment is not None:
        project.manager_comment = status_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


@app.patch(
    "/{project_id}/approve",
    response_model=schemas.ProjectResponse,
    tags=["projects"],
    summary="Approve a project",
)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(status_code=403, detail="Only managers or admins can approve")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus.approved
    project.manager_comment = None
    db.commit()
    db.refresh(project)
    return project


@app.patch(
    "/{project_id}/reject",
    response_model=schemas.ProjectResponse,
    tags=["projects"],
    summary="Reject a project with a comment",
)
def reject_project(
    project_id: int,
    reject_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(status_code=403, detail="Only managers or admins can reject")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus.rejected
    project.manager_comment = reject_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


@app.post(
    "/{project_id}/measures",
    response_model=schemas.MeasureResponse,
    status_code=201,
    tags=["measures"],
    summary="Attach a measure to a project",
)
def add_measure(
    project_id: int,
    measure_data: schemas.MeasureCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot add measures")
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] != "admin":
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    measure = models.Measure(
        project_id=project_id,
        **measure_data.model_dump(),
    )
    db.add(measure)
    db.commit()
    db.refresh(measure)
    return measure


@app.patch(
    "/{project_id}/measures/{measure_id}",
    response_model=schemas.MeasureResponse,
    tags=["measures"],
    summary="Update a measure's parameters",
)
def update_measure(
    project_id: int,
    measure_id: int,
    update_data: schemas.MeasureUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot edit measures")
    q = (
        db.query(models.Measure)
        .filter(models.Measure.id == measure_id)
        .filter(models.Measure.project_id == project_id)
    )
    if current_user["role"] != "admin":
        q = q.join(models.Project).filter(models.Project.owner_id == _require_user_id(current_user))
    measure = q.first()
    if not measure:
        raise HTTPException(status_code=404, detail="Measure not found")
    payload = update_data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(measure, field, value)
    db.commit()
    db.refresh(measure)
    return measure


@app.delete(
    "/{project_id}/measures/{measure_id}",
    tags=["measures"],
    summary="Delete a measure from a project",
)
def delete_measure(
    project_id: int,
    measure_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if current_user["role"] == "manager":
        raise HTTPException(status_code=403, detail="Managers cannot delete measures")
    q = (
        db.query(models.Measure)
        .filter(models.Measure.id == measure_id)
        .filter(models.Measure.project_id == project_id)
    )
    if current_user["role"] != "admin":
        q = q.join(models.Project).filter(models.Project.owner_id == _require_user_id(current_user))
    measure = q.first()
    if not measure:
        raise HTTPException(status_code=404, detail="Measure not found")
    db.delete(measure)
    db.commit()
    return {"message": "Measure deleted"}


# ─── Orchestrated full analysis ─────────────────────────────────────────────


_DEFAULT_AHP_MATRIX = [
    [1, 2, 2, 3],
    [1 / 2, 1, 1, 2],
    [1 / 2, 1, 1, 2],
    [1 / 3, 1 / 2, 1 / 2, 1],
]
_DEFAULT_AHP_CRITERIA = ["npv", "irr", "co2", "payback"]
_DEFAULT_AHP_IS_BENEFIT = [True, True, True, False]


def _load_project_with_measures(db: Session, project_id: int, current_user: dict) -> models.Project:
    q = db.query(models.Project).filter(models.Project.id == project_id)
    if not _is_privileged(current_user["role"]):
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.measures:
        raise HTTPException(status_code=422, detail="Project has no measures to analyse")
    return project


@app.post(
    "/{project_id}/analyze/full",
    response_model=schemas.FullAnalysisResponse,
    tags=["analysis"],
    summary="Run every calculator (financial + eco + AHP + TOPSIS + sensitivity + comparison)",
)
async def analyze_full(
    project_id: int,
    payload: schemas.FullAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    project = _load_project_with_measures(db, project_id, current_user)
    token: str = current_user["token"]
    fuel_factor = _FUEL_FACTORS[payload.fuel_type]

    financial_body = {
        "measures": [
            {
                "name": m.name,
                "initial_investment": m.initial_investment,
                "operational_cost": m.operational_cost,
                "expected_savings": m.expected_savings,
                "lifetime_years": m.lifetime_years,
                "discount_rate": payload.discount_rate,
            }
            for m in project.measures
        ],
        "discount_rate": payload.discount_rate,
    }
    # Project stores emission_reduction in tons CO2/year, but the eco
    # service expects consumption units. tons * (1000 / factor_kg_per_unit)
    # recovers the original fuel-unit quantity.
    eco_body = {
        "measures": [
            {
                "name": m.name,
                "fuel_type": payload.fuel_type,
                "annual_consumption_reduction": (
                    m.emission_reduction * (1000.0 / fuel_factor) if fuel_factor > 0 else 0.0
                ),
                "co2_price_per_ton": payload.co2_price_per_ton,
                "damage_coefficient": payload.damage_coefficient,
            }
            for m in project.measures
        ],
    }

    api = InternalAPI()

    try:
        financial_res, eco_res = await asyncio.gather(
            api.post_financial_portfolio(financial_body, token),
            api.post_eco_portfolio(eco_body, token),
        )
    except (CircuitBreakerOpen, RemoteServiceError) as exc:
        logger.warning("Full analysis upstream failure: %s", exc)
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    alternatives = []
    for i, m in enumerate(project.measures):
        f_row = financial_res["results"][i]
        e_row = eco_res["results"][i]
        irr_val = (
            f_row.get("irr", {}).get("value")
            if isinstance(f_row.get("irr"), dict)
            else f_row.get("irr")
        )
        simple_payback = f_row.get("simple_payback")
        alternatives.append(
            {
                "name": m.name,
                "npv": f_row.get("npv", 0.0),
                "irr": irr_val if irr_val is not None else 0.0,
                "co2": e_row.get("co2_reduction_tons_per_year", 0.0),
                "payback": simple_payback if simple_payback and simple_payback > 0 else 999,
            }
        )

    ahp_res: dict | None = None
    topsis_res: dict | None = None
    try:
        ahp_res = await api.post_ahp(
            {
                "criteria": _DEFAULT_AHP_CRITERIA,
                "comparison_matrix": _DEFAULT_AHP_MATRIX,
                "alternatives": alternatives,
                "is_benefit": _DEFAULT_AHP_IS_BENEFIT,
            },
            token,
        )
        topsis_res = await api.post_topsis(
            {
                "criteria": _DEFAULT_AHP_CRITERIA,
                "weights": ahp_res["weights"],
                "is_benefit": _DEFAULT_AHP_IS_BENEFIT,
                "alternatives": alternatives,
            },
            token,
        )
    except (CircuitBreakerOpen, RemoteServiceError) as exc:
        logger.warning("AHP/TOPSIS optional step failed: %s", exc)

    ahp_score_by_name = {r["name"]: r["score"] for r in ahp_res["ranking"]} if ahp_res else {}
    topsis_score_by_name = (
        {r["name"]: r["closeness_coefficient"] for r in topsis_res["ranking"]} if topsis_res else {}
    )

    comparison_measures = []
    for i, m in enumerate(project.measures):
        f_row = financial_res["results"][i]
        e_row = eco_res["results"][i]
        irr_val = (
            f_row.get("irr", {}).get("value")
            if isinstance(f_row.get("irr"), dict)
            else f_row.get("irr")
        )
        comparison_measures.append(
            {
                "name": m.name,
                "npv": f_row.get("npv", 0.0),
                "irr": irr_val,
                "bcr": f_row.get("bcr"),
                "simple_payback": f_row.get("simple_payback"),
                "co2_reduction": e_row.get("co2_reduction_tons_per_year", 0.0),
                "ahp_score": ahp_score_by_name.get(m.name),
                "topsis_score": topsis_score_by_name.get(m.name),
            }
        )

    try:
        comparison_res = await api.post_comparison({"measures": comparison_measures}, token)
    except (CircuitBreakerOpen, RemoteServiceError) as exc:
        logger.warning("Full analysis comparison failure: %s", exc)
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    sensitivity_res: dict | None = None
    try:
        first = project.measures[0]
        sensitivity_res = await api.post_sensitivity(
            {
                "base": {
                    "name": first.name,
                    "initial_investment": first.initial_investment,
                    "operational_cost": first.operational_cost,
                    "expected_savings": first.expected_savings,
                    "lifetime_years": first.lifetime_years,
                    "discount_rate": payload.discount_rate,
                },
                "variation_percent": payload.sensitivity_variation_percent,
                "steps": 3,
            },
            token,
        )
    except (CircuitBreakerOpen, RemoteServiceError) as exc:
        logger.warning("Sensitivity optional step failed: %s", exc)

    logger.info(
        "Full analysis for project %s: %d measures, best=%s",
        project_id,
        len(project.measures),
        comparison_res.get("best_consensus"),
    )

    return schemas.FullAnalysisResponse(
        project_id=project.id,
        project_name=project.name,
        discount_rate=payload.discount_rate,
        financial=financial_res,
        eco=eco_res,
        ahp=ahp_res,
        topsis=topsis_res,
        comparison=comparison_res,
        sensitivity=sensitivity_res,
    )
