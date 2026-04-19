"""Lightweight CRUD wrapper around ``FinancialResult`` rows.

Lifted to ``eco_common`` in Phase 3.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import FinancialResult

VERSION = 1


def save_result(
    db: Session,
    *,
    project_id: int,
    input_data: dict,
    result_data: dict,
) -> FinancialResult:
    row = FinancialResult(
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


def list_for_project(db: Session, project_id: int) -> List[FinancialResult]:
    return (
        db.query(FinancialResult)
        .filter(FinancialResult.project_id == project_id)
        .order_by(FinancialResult.id.desc())
        .all()
    )


def get_one(db: Session, result_id: int) -> Optional[FinancialResult]:
    return db.query(FinancialResult).filter(FinancialResult.id == result_id).first()
