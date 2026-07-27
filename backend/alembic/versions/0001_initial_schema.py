"""Initial schema.

The first migration materializes the full model set from SQLAlchemy metadata.
Subsequent migrations should be generated with `alembic revision --autogenerate`
and contain explicit operations.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-27
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# Import models so metadata is populated when this migration runs.
import app.models  # noqa: F401
from app.db.base import Base

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
