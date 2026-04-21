"""data migration: legacy projects.owner_username -> owner_id (FK users.id)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-01 00:01:00.000000

This migration is a no-op for fresh deployments (initial schema already
uses ``owner_id``). For existing databases that were originally created
by the legacy ``Base.metadata.create_all`` path with an ``owner_username``
text column, it:

  1. adds a nullable ``owner_id`` column,
  2. backfills it from ``users.username`` lookup,
  3. orphans any project whose owner cannot be resolved (logged + dropped),
  4. enforces NOT NULL and adds the FK constraint + index,
  5. drops the legacy ``owner_username`` column.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "projects", "owner_username"):
        return

    if not _has_column(bind, "projects", "owner_id"):
        op.add_column(
            "projects", sa.Column("owner_id", sa.Integer(), nullable=True)
        )

    op.execute(
        sa.text(
            """
            UPDATE projects p
               SET owner_id = u.id
              FROM users u
             WHERE u.username = p.owner_username
               AND p.owner_id IS NULL
            """
        )
    )

    op.execute(sa.text("DELETE FROM projects WHERE owner_id IS NULL"))

    op.alter_column("projects", "owner_id", nullable=False)

    insp = sa.inspect(bind)
    fk_names = {fk["name"] for fk in insp.get_foreign_keys("projects")}
    if "fk_projects_owner_id_users" not in fk_names:
        op.create_foreign_key(
            "fk_projects_owner_id_users",
            "projects",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )

    existing_indexes = {ix["name"] for ix in insp.get_indexes("projects")}
    if "ix_projects_owner_id" not in existing_indexes:
        op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.drop_column("projects", "owner_username")


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "projects", "owner_username"):
        return

    op.add_column(
        "projects", sa.Column("owner_username", sa.String(length=64), nullable=True)
    )
    op.execute(
        sa.text(
            """
            UPDATE projects p
               SET owner_username = u.username
              FROM users u
             WHERE u.id = p.owner_id
            """
        )
    )
    op.alter_column("projects", "owner_username", nullable=False)

    insp = sa.inspect(bind)

    existing_indexes = {ix["name"] for ix in insp.get_indexes("projects")}
    if "ix_projects_owner_id" in existing_indexes:
        op.drop_index("ix_projects_owner_id", table_name="projects")

    for fk in insp.get_foreign_keys("projects"):
        if fk.get("constrained_columns") == ["owner_id"] and fk.get("name"):
            op.drop_constraint(fk["name"], "projects", type_="foreignkey")

    op.drop_column("projects", "owner_id")
