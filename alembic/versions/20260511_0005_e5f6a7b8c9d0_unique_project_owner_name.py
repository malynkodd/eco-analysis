"""unique constraint on (owner_id, name) in projects

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-11 00:02:00.000000

Prevents a single owner from having two projects with the same name
at the database level.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {
        c["name"]
        for c in sa.inspect(bind).get_unique_constraints("projects")
    }
    if "uq_projects_owner_name" not in existing:
        op.create_unique_constraint("uq_projects_owner_name", "projects", ["owner_id", "name"])


def downgrade() -> None:
    op.drop_constraint("uq_projects_owner_name", "projects", type_="unique")
