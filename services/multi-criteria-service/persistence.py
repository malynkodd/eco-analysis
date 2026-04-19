"""CRUD wrappers around ``AHPResult`` and ``TopsisResult`` rows."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import AHPResult as AHPResultRow
from db.models import TopsisResult as TopsisResultRow

VERSION = 1


def _save(db: Session, row):
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_ahp(
    db: Session, *, project_id: int, input_data: dict, result_data: dict
) -> AHPResultRow:
    return _save(
        db,
        AHPResultRow(
            project_id=project_id,
            input_data=input_data,
            result_data=result_data,
            version=VERSION,
            status="completed",
        ),
    )


def save_topsis(
    db: Session, *, project_id: int, input_data: dict, result_data: dict
) -> TopsisResultRow:
    return _save(
        db,
        TopsisResultRow(
            project_id=project_id,
            input_data=input_data,
            result_data=result_data,
            version=VERSION,
            status="completed",
        ),
    )


def list_ahp(db: Session, project_id: int) -> List[AHPResultRow]:
    return (
        db.query(AHPResultRow)
        .filter(AHPResultRow.project_id == project_id)
        .order_by(AHPResultRow.id.desc())
        .all()
    )


def list_topsis(db: Session, project_id: int) -> List[TopsisResultRow]:
    return (
        db.query(TopsisResultRow)
        .filter(TopsisResultRow.project_id == project_id)
        .order_by(TopsisResultRow.id.desc())
        .all()
    )


def get_ahp(db: Session, result_id: int) -> Optional[AHPResultRow]:
    return db.query(AHPResultRow).filter(AHPResultRow.id == result_id).first()


def get_topsis(db: Session, result_id: int) -> Optional[TopsisResultRow]:
    return db.query(TopsisResultRow).filter(TopsisResultRow.id == result_id).first()
