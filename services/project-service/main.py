"""Project service — CRUD for projects and measures.

Authorization model:
  * analyst — owns the projects they create; can manage their own.
  * manager — read-only on projects; can approve/reject.
  * admin   — full access to every project.
"""

from __future__ import annotations

import auth
import models
import schemas
from database import get_db
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from eco_common.api_setup import create_app
from eco_common.envelope import paginate

OPENAPI_TAGS = [
    {"name": "projects", "description": "Project lifecycle and approval."},
    {"name": "measures", "description": "Energy-efficiency measures attached to a project."},
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
