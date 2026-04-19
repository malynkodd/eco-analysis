import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

# Migrate existing tables — add columns added after initial deploy
with engine.connect() as _conn:
    _conn.execute(text(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'pending'"
    ))
    _conn.execute(text(
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS manager_comment TEXT"
    ))
    _conn.commit()


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


# ─── ПРОЄКТИ ──────────────────────────────────────────

@app.post("/", response_model=schemas.ProjectResponse)
def create_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Створити новий проєкт — тільки аналітик і адмін"""
    if current_user["role"] == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Менеджер не може створювати проєкти"
        )
    project = models.Project(
        name=project_data.name,
        description=project_data.description,
        owner_username=current_user["username"],
        status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/", response_model=List[schemas.ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Отримати проєкти.
    Менеджер/адмін бачить усі; аналітик — тільки свої.
    """
    if current_user["role"] in ("manager", "admin"):
        return db.query(models.Project).all()
    return db.query(models.Project).filter(
        models.Project.owner_username == current_user["username"]
    ).all()


@app.get("/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Отримати один проєкт по ID"""
    query = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] not in ("manager", "admin"):
        query = query.filter(models.Project.owner_username == current_user["username"])
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    return project


@app.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Видалити проєкт (тільки власник або адмін)"""
    if current_user["role"] == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Менеджер не може видаляти проєкти"
        )
    query = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] != "admin":
        query = query.filter(models.Project.owner_username == current_user["username"])
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    db.delete(project)
    db.commit()
    return {"message": "Проєкт видалено"}


@app.patch("/{project_id}/status", response_model=schemas.ProjectResponse)
def update_project_status(
    project_id: int,
    status_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Змінити статус проєкту: approved / rejected / pending.
    Доступно тільки менеджеру та адміністратору.
    """
    if current_user["role"] not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки менеджер або адміністратор може змінювати статус"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    project.status = status_data.status
    if status_data.manager_comment is not None:
        project.manager_comment = status_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


@app.patch("/{project_id}/approve", response_model=schemas.ProjectResponse)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Затвердити проєкт (тільки менеджер/адмін)"""
    if current_user["role"] not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки менеджер або адміністратор може затверджувати проєкти"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    project.status = "approved"
    project.manager_comment = None
    db.commit()
    db.refresh(project)
    return project


@app.patch("/{project_id}/reject", response_model=schemas.ProjectResponse)
def reject_project(
    project_id: int,
    reject_data: schemas.StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Відхилити проєкт з опціональним коментарем (тільки менеджер/адмін)"""
    if current_user["role"] not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки менеджер або адміністратор може відхиляти проєкти"
        )
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")
    project.status = "rejected"
    project.manager_comment = reject_data.manager_comment
    db.commit()
    db.refresh(project)
    return project


# ─── ЗАХОДИ ───────────────────────────────────────────

@app.post("/{project_id}/measures", response_model=schemas.MeasureResponse)
def add_measure(
    project_id: int,
    measure_data: schemas.MeasureCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Додати захід до проєкту — тільки власник (аналітик) або адмін"""
    if current_user["role"] == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Менеджер не може додавати заходи"
        )
    query = db.query(models.Project).filter(models.Project.id == project_id)
    if current_user["role"] != "admin":
        query = query.filter(models.Project.owner_username == current_user["username"])
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="Проєкт не знайдено")

    measure = models.Measure(
        project_id=project_id,
        **measure_data.model_dump()
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
    current_user: dict = Depends(auth.get_current_user)
):
    """Видалити захід з проєкту — тільки власник або адмін"""
    if current_user["role"] == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Менеджер не може видаляти заходи"
        )
    measure = db.query(models.Measure).filter(
        models.Measure.id == measure_id,
        models.Measure.project_id == project_id
    ).first()
    if not measure:
        raise HTTPException(status_code=404, detail="Захід не знайдено")
    db.delete(measure)
    db.commit()
    return {"message": "Захід видалено"}
