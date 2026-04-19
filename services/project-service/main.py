"""Project service — CRUD for projects and measures.

Authorization model:
  * analyst — owns the projects they create; can manage their own.
  * manager — read-only on projects; can approve/reject.
  * admin   — full access to every project.

The current user is identified by ``user_id`` (FK to ``users.id``)
extracted from the RS256 JWT.
"""
from __future__ import annotations

import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Project Service",
    root_path="/api/v1/projects",
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
    return {"status": "ok", "service": "project-service"}


# ─── helpers ─────────────────────────────────────────────────────────────────


def _require_user_id(current_user: dict) -> int:
    uid = current_user.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="Token missing user id")
    return int(uid)


def _is_privileged(role: str) -> bool:
    return role in ("manager", "admin")


# ─── PROJECTS ────────────────────────────────────────────────────────────────


@app.post("/", response_model=schemas.ProjectResponse, status_code=201)
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


@app.get("/", response_model=List[schemas.ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    q = db.query(models.Project)
    if not _is_privileged(current_user["role"]):
        q = q.filter(models.Project.owner_id == _require_user_id(current_user))
    return q.order_by(models.Project.id.desc()).all()


@app.get("/{project_id}", response_model=schemas.ProjectResponse)
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


@app.delete("/{project_id}")
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


@app.patch("/{project_id}/status", response_model=schemas.ProjectResponse)
def update_project_status(
    project_id: int,
    status_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(
            status_code=403, detail="Only managers or admins can change status"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus(status_data.status)
    if status_data.manager_comment is not None:
        project.manager_comment = status_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


@app.patch("/{project_id}/approve", response_model=schemas.ProjectResponse)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(
            status_code=403, detail="Only managers or admins can approve"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus.approved
    project.manager_comment = None
    db.commit()
    db.refresh(project)
    return project


@app.patch("/{project_id}/reject", response_model=schemas.ProjectResponse)
def reject_project(
    project_id: int,
    reject_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user),
):
    if not _is_privileged(current_user["role"]):
        raise HTTPException(
            status_code=403, detail="Only managers or admins can reject"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = models.ProjectStatus.rejected
    project.manager_comment = reject_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


# ─── MEASURES ────────────────────────────────────────────────────────────────


@app.post(
    "/{project_id}/measures",
    response_model=schemas.MeasureResponse,
    status_code=201,
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


@app.delete("/{project_id}/measures/{measure_id}")
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
        q = q.join(models.Project).filter(
            models.Project.owner_id == _require_user_id(current_user)
        )
    measure = q.first()
    if not measure:
        raise HTTPException(status_code=404, detail="Measure not found")
    db.delete(measure)
    db.commit()
    return {"message": "Measure deleted"}
