"""Add opening repertoire entries.

Revision ID: 0002_repertoire
Revises: 0001_initial
Create Date: 2026-07-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_repertoire"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repertoire_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("eco", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("color", sa.String(length=5), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "eco", "color", name="uq_repertoire_user_eco_color"),
    )
    op.create_index(
        op.f("ix_repertoire_entries_user_id"), "repertoire_entries", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_repertoire_entries_user_id"), table_name="repertoire_entries")
    op.drop_table("repertoire_entries")
