"""CRUD wrapper around ``ScenarioResult`` rows."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import ScenarioResult

VERSION = 1


def save_result(
    db: Session,
    *,
    project_id: int,
    input_data: dict,
    result_data: dict,
) -> ScenarioResult:
    row = ScenarioResult(
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


def list_for_project(db: Session, project_id: int) -> List[ScenarioResult]:
    return (
        db.query(ScenarioResult)
        .filter(ScenarioResult.project_id == project_id)
        .order_by(ScenarioResult.id.desc())
        .all()
    )


def get_one(db: Session, result_id: int) -> Optional[ScenarioResult]:
    return db.query(ScenarioResult).filter(ScenarioResult.id == result_id).first()
