"""Migrations must run cleanly on an empty database.

This is the exact path a production deploy takes (the container runs
`alembic upgrade head` on boot against a fresh Postgres). Regression guard for a
bug where the initial migration built tables from *live* model metadata, so a
fresh database got later revisions' tables early and the next migration then
failed with "table already exists".
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect

BACKEND = pathlib.Path(__file__).resolve().parents[1]

# Tables the application expects once every migration has run.
EXPECTED = {
    "users", "weakness_profiles", "games", "moves", "move_analyses",
    "game_reviews", "training_plans", "training_weeks", "puzzles",
    "puzzle_attempts", "bookmarks", "repertoire_entries", "follows",
}


@pytest.fixture()
def fresh_db(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'fresh.db'}"


def test_upgrade_head_on_empty_database(fresh_db, tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env={"PATH": "/usr/bin:/bin", "DATABASE_URL": fresh_db, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic failed:\n{result.stderr}"

    inspector = inspect(create_engine(fresh_db))
    tables = set(inspector.get_table_names())
    missing = EXPECTED - tables
    assert not missing, f"missing tables after upgrade: {sorted(missing)}"

    # share_token is added by a later revision; prove the ALTER actually applied.
    columns = {c["name"] for c in inspector.get_columns("games")}
    assert "share_token" in columns
