"""add new measure_type enum values

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-11 00:00:00.000000

Adds 6 new values to the measure_type PostgreSQL enum:
  led_lighting, heat_recovery, boiler_modernization,
  energy_monitoring, ev_electrification, wastewater_reuse
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_VALUES = (
    "led_lighting",
    "heat_recovery",
    "boiler_modernization",
    "energy_monitoring",
    "ev_electrification",
    "wastewater_reuse",
)


def upgrade() -> None:
    bind = op.get_bind()
    for value in _NEW_VALUES:
        bind.execute(
            sa.text(f"ALTER TYPE measure_type ADD VALUE IF NOT EXISTS '{value}'")
        )


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum values.
    # To downgrade, recreate the type with only the original four values,
    # converting any rows that use the removed values to NULL first.
    bind = op.get_bind()

    removed = ", ".join(f"'{v}'" for v in _NEW_VALUES)
    bind.execute(
        sa.text(
            f"UPDATE measures SET measure_type = NULL "
            f"WHERE measure_type::text IN ({removed})"
        )
    )

    bind.execute(
        sa.text(
            "CREATE TYPE measure_type_old AS ENUM "
            "('insulation','equipment','treatment','renewable')"
        )
    )
    bind.execute(
        sa.text(
            "ALTER TABLE measures "
            "ALTER COLUMN measure_type TYPE measure_type_old "
            "USING measure_type::text::measure_type_old"
        )
    )
    bind.execute(sa.text("DROP TYPE measure_type"))
    bind.execute(sa.text("ALTER TYPE measure_type_old RENAME TO measure_type"))
