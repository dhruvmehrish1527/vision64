"""Add follows and shareable game links.

Revision ID: 0003_social
Revises: 0002_repertoire
Create Date: 2026-07-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_social"
down_revision: Union[str, None] = "0002_repertoire"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "follows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("following_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),
        sa.CheckConstraint("follower_id != following_id", name="ck_follow_not_self"),
    )
    op.create_index(op.f("ix_follows_follower_id"), "follows", ["follower_id"])
    op.create_index(op.f("ix_follows_following_id"), "follows", ["following_id"])

    # Batch mode keeps this ALTER working on SQLite as well as PostgreSQL.
    with op.batch_alter_table("games") as batch:
        batch.add_column(sa.Column("share_token", sa.String(length=32), nullable=True))
        batch.create_index("ix_games_share_token", ["share_token"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.drop_index("ix_games_share_token")
        batch.drop_column("share_token")

    op.drop_index(op.f("ix_follows_following_id"), table_name="follows")
    op.drop_index(op.f("ix_follows_follower_id"), table_name="follows")
    op.drop_table("follows")
