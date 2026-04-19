"""initial schema — users, projects, measures, result tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-01-01 00:00:00.000000

This migration is idempotent so it can stamp legacy deployments that
were originally created via ``Base.metadata.create_all``: every table /
index / enum is created with ``checkfirst=True`` semantics, and missing
columns are added one-by-one.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_ROLE = postgresql.ENUM(
    "analyst", "manager", "admin", name="user_role", create_type=False
)
PROJECT_STATUS = postgresql.ENUM(
    "pending", "approved", "rejected", name="project_status", create_type=False
)
MEASURE_TYPE = postgresql.ENUM(
    "insulation",
    "equipment",
    "treatment",
    "renewable",
    name="measure_type",
    create_type=False,
)


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def _column_exists(bind, table: str, column: str) -> bool:
    if not _table_exists(bind, table):
        return False
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def _ensure_index(bind, table: str, name: str, cols, *, unique: bool = False) -> None:
    existing = {ix["name"] for ix in sa.inspect(bind).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, cols, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE user_role AS ENUM ('analyst','manager','admin'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
    )
    bind.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE project_status AS ENUM ('pending','approved','rejected'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
    )
    bind.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE measure_type AS ENUM "
            "('insulation','equipment','treatment','renewable'); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )
    )

    if not _table_exists(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", USER_ROLE, nullable=False, server_default="analyst"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("email", name="uq_users_email"),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )
    else:
        if not _column_exists(bind, "users", "created_at"):
            op.add_column(
                "users",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
        if not _column_exists(bind, "users", "updated_at"):
            op.add_column(
                "users",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
    _ensure_index(bind, "users", "ix_users_email", ["email"], unique=True)
    _ensure_index(bind, "users", "ix_users_username", ["username"], unique=True)

    if not _table_exists(bind, "projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "owner_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "status",
                PROJECT_STATUS,
                nullable=False,
                server_default="pending",
            ),
            sa.Column("manager_comment", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    else:
        if not _column_exists(bind, "projects", "manager_comment"):
            op.add_column(
                "projects", sa.Column("manager_comment", sa.Text(), nullable=True)
            )
        if not _column_exists(bind, "projects", "created_at"):
            op.add_column(
                "projects",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
        if not _column_exists(bind, "projects", "updated_at"):
            op.add_column(
                "projects",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
    _ensure_index(bind, "projects", "ix_projects_status", ["status"])
    if _column_exists(bind, "projects", "owner_id"):
        _ensure_index(bind, "projects", "ix_projects_owner_id", ["owner_id"])

    if not _table_exists(bind, "measures"):
        op.create_table(
            "measures",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("measure_type", MEASURE_TYPE, nullable=False),
            sa.Column("initial_investment", sa.Float(), nullable=False),
            sa.Column("operational_cost", sa.Float(), nullable=False),
            sa.Column("expected_savings", sa.Float(), nullable=False),
            sa.Column("lifetime_years", sa.Integer(), nullable=False),
            sa.Column("emission_reduction", sa.Float(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    else:
        if not _column_exists(bind, "measures", "created_at"):
            op.add_column(
                "measures",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
        if not _column_exists(bind, "measures", "updated_at"):
            op.add_column(
                "measures",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
    _ensure_index(bind, "measures", "ix_measures_project_id", ["project_id"])

    for tbl in (
        "financial_results",
        "ahp_results",
        "topsis_results",
        "eco_results",
        "scenario_results",
    ):
        if not _table_exists(bind, tbl):
            op.create_table(
                tbl,
                sa.Column("id", sa.BigInteger(), primary_key=True),
                sa.Column(
                    "project_id",
                    sa.Integer(),
                    sa.ForeignKey("projects.id", ondelete="CASCADE"),
                    nullable=False,
                ),
                sa.Column("input_data", postgresql.JSONB(), nullable=False),
                sa.Column("result_data", postgresql.JSONB(), nullable=False),
                sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
                sa.Column(
                    "status",
                    sa.String(length=32),
                    nullable=False,
                    server_default="completed",
                ),
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
        _ensure_index(bind, tbl, f"ix_{tbl}_project_id", ["project_id"])

    if not _table_exists(bind, "comparison_results"):
        op.create_table(
            "comparison_results",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("input_data", postgresql.JSONB(), nullable=False),
            sa.Column("result_data", postgresql.JSONB(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="completed",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "project_id", "version", name="uq_comparison_project_version"
            ),
        )
    _ensure_index(
        bind,
        "comparison_results",
        "ix_comparison_results_project_id",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_comparison_results_project_id", table_name="comparison_results"
    )
    op.drop_table("comparison_results")
    for tbl in (
        "scenario_results",
        "eco_results",
        "topsis_results",
        "ahp_results",
        "financial_results",
    ):
        op.drop_index(f"ix_{tbl}_project_id", table_name=tbl)
        op.drop_table(tbl)
    op.drop_index("ix_measures_project_id", table_name="measures")
    op.drop_table("measures")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS measure_type")
    op.execute("DROP TYPE IF EXISTS project_status")
    op.execute("DROP TYPE IF EXISTS user_role")
