"""Following relationships between users."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Follow(Base):
    """`follower_id` follows `following_id`.

    A unique constraint makes following idempotent, and a check constraint stops
    a user following themselves at the database level (not just in app code).
    """

    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),
        CheckConstraint("follower_id != following_id", name="ck_follow_not_self"),
    )

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
