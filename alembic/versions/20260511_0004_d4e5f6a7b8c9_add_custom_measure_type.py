"""add custom value to measure_type enum

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-11 00:01:00.000000

Adds the 'custom' value to the measure_type PostgreSQL enum so users
can create measures with a free-form type name.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("ALTER TYPE measure_type ADD VALUE IF NOT EXISTS 'custom'")
    )


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum values.
    # Rows with measure_type='custom' are nulled out, then the type is
    # recreated without 'custom'.
    bind = op.get_bind()

    bind.execute(
        sa.text("UPDATE measures SET measure_type = NULL WHERE measure_type::text = 'custom'")
    )
    bind.execute(
        sa.text(
            "CREATE TYPE measure_type_no_custom AS ENUM ("
            "'insulation','equipment','treatment','renewable',"
            "'led_lighting','heat_recovery','boiler_modernization',"
            "'energy_monitoring','ev_electrification','wastewater_reuse')"
        )
    )
    bind.execute(
        sa.text(
            "ALTER TABLE measures "
            "ALTER COLUMN measure_type TYPE measure_type_no_custom "
            "USING measure_type::text::measure_type_no_custom"
        )
    )
    bind.execute(sa.text("DROP TYPE measure_type"))
    bind.execute(sa.text("ALTER TYPE measure_type_no_custom RENAME TO measure_type"))
