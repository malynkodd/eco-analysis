"""CRUD wrapper around ``EcoResult`` rows."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import EcoResult

VERSION = 1


def save_result(
    db: Session,
    *,
    project_id: int,
    input_data: dict,
    result_data: dict,
) -> EcoResult:
    row = EcoResult(
        project_id=project_id,
        input_data=input_data,
        result_data=result_data,
        version=VERSION,
        status="completed",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_project(db: Session, project_id: int) -> List[EcoResult]:
    return (
        db.query(EcoResult)
        .filter(EcoResult.project_id == project_id)
        .order_by(EcoResult.id.desc())
        .all()
    )


def get_one(db: Session, result_id: int) -> Optional[EcoResult]:
    return db.query(EcoResult).filter(EcoResult.id == result_id).first()
