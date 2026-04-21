"""CRUD wrapper around ``ComparisonResult`` rows."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ComparisonResult

VERSION = 1


def _next_version(db: Session, project_id: int) -> int:
    last = (
        db.query(func.max(ComparisonResult.version))
        .filter(ComparisonResult.project_id == project_id)
        .scalar()
    )
    return (last or 0) + 1


def save_result(
    db: Session,
    *,
    project_id: int,
    input_data: dict,
    result_data: dict,
) -> ComparisonResult:
    row = ComparisonResult(
        project_id=project_id,
        input_data=input_data,
        result_data=result_data,
        version=_next_version(db, project_id),
        status="completed",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_project(db: Session, project_id: int) -> List[ComparisonResult]:
    return (
        db.query(ComparisonResult)
        .filter(ComparisonResult.project_id == project_id)
        .order_by(ComparisonResult.version.desc())
        .all()
    )


def get_one(db: Session, result_id: int) -> Optional[ComparisonResult]:
    return db.query(ComparisonResult).filter(ComparisonResult.id == result_id).first()
