"""Initial schema.

Tables are declared **explicitly** rather than via `Base.metadata.create_all()`.
A migration must describe the schema as it stood at *this* revision — reading
live model metadata would make it create whatever the models look like today,
so later migrations would then fail trying to add tables/columns that already
exist. (That is exactly what happened before this was fixed: a fresh database
got `repertoire_entries` from 0001 and then 0002 crashed on "table exists".)

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Timestamp columns every table carries (from the declarative Base).
def _stamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _pk() -> sa.Column:
    return sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True)


def upgrade() -> None:
    op.create_table(
        "users",
        _pk(),
        *_stamps(),
        sa.Column("clerk_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("puzzle_rating", sa.Integer(), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("training_seconds", sa.Integer(), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)

    op.create_table(
        "weakness_profiles",
        _pk(),
        *_stamps(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("patterns", sa.JSON(), nullable=False),
        sa.Column("games_analyzed", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_weakness_profiles_user_id", "weakness_profiles", ["user_id"], unique=True
    )

    op.create_table(
        "games",
        _pk(),
        *_stamps(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pgn", sa.Text(), nullable=True),
        sa.Column("initial_fen", sa.String(length=120), nullable=False),
        sa.Column("white", sa.String(length=120), nullable=True),
        sa.Column("black", sa.String(length=120), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("event", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("accuracy_white", sa.Float(), nullable=True),
        sa.Column("accuracy_black", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_games_user_id", "games", ["user_id"])

    op.create_table(
        "moves",
        _pk(),
        *_stamps(),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("san", sa.String(length=16), nullable=False),
        sa.Column("uci", sa.String(length=8), nullable=False),
        sa.Column("fen_before", sa.String(length=120), nullable=False),
        sa.Column("fen_after", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=5), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_moves_game_id", "moves", ["game_id"])

    op.create_table(
        "move_analyses",
        _pk(),
        *_stamps(),
        sa.Column("move_id", sa.Integer(), nullable=False),
        sa.Column("eval_cp", sa.Integer(), nullable=True),
        sa.Column("mate_in", sa.Integer(), nullable=True),
        sa.Column("best_move", sa.String(length=8), nullable=True),
        sa.Column("pv", sa.JSON(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("classification", sa.String(length=16), nullable=True),
        sa.Column("centipawn_loss", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["move_id"], ["moves.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_move_analyses_move_id", "move_analyses", ["move_id"], unique=True)

    op.create_table(
        "game_reviews",
        _pk(),
        *_stamps(),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("biggest_mistake_ply", sa.Integer(), nullable=True),
        sa.Column("phases", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_game_reviews_game_id", "game_reviews", ["game_id"], unique=True)

    op.create_table(
        "training_plans",
        _pk(),
        *_stamps(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_training_plans_user_id", "training_plans", ["user_id"])

    op.create_table(
        "training_weeks",
        _pk(),
        *_stamps(),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("focus_topics", sa.JSON(), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["training_plans.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_training_weeks_plan_id", "training_weeks", ["plan_id"])

    op.create_table(
        "puzzles",
        _pk(),
        *_stamps(),
        sa.Column("fen", sa.String(length=120), nullable=False),
        sa.Column("solution_uci", sa.JSON(), nullable=False),
        sa.Column("theme", sa.String(length=32), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_puzzles_theme", "puzzles", ["theme"])

    op.create_table(
        "puzzle_attempts",
        _pk(),
        *_stamps(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("puzzle_id", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("time_ms", sa.Integer(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_puzzle_attempts_user_id", "puzzle_attempts", ["user_id"])
    op.create_index("ix_puzzle_attempts_puzzle_id", "puzzle_attempts", ["puzzle_id"])

    op.create_table(
        "bookmarks",
        _pk(),
        *_stamps(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])


def downgrade() -> None:
    for table in [
        "bookmarks",
        "puzzle_attempts",
        "puzzles",
        "training_weeks",
        "training_plans",
        "game_reviews",
        "move_analyses",
        "moves",
        "games",
        "weakness_profiles",
        "users",
    ]:
        op.drop_table(table)
