"""SQLAlchemy declarative base and cross-dialect JSON type.

`Base` is imported by every model and by Alembic's `target_metadata`. The
`JSONB`-or-`JSON` helper lets the same models run on PostgreSQL in production
and SQLite locally without change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

# Prefer Postgres JSONB when available; fall back to generic JSON (SQLite).
try:  # pragma: no cover - import guard
    from sqlalchemy.dialects.postgresql import JSONB

    JSONType = JSON().with_variant(JSONB(), "postgresql")
except Exception:  # pragma: no cover
    JSONType = JSON()


def utcnow() -> datetime:
    """Timezone-aware UTC now — used as the default for all timestamps."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base with an integer primary key and timestamps."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
