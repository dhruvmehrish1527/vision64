"""User and per-user weakness aggregate."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, utcnow

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.training import TrainingPlan


class User(Base):
    """A Vision64 user, keyed to a Clerk identity.

    We keep our own row (rather than reading everything from Clerk) so chess
    data — rating, puzzle rating, streak — is queryable and joinable locally.
    """

    __tablename__ = "users"

    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Self-reported / estimated playing strength (Elo). Drives coach adaptation.
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    puzzle_rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)

    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    training_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    games: Mapped[list["Game"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    weakness_profile: Mapped["WeaknessProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    training_plans: Mapped[list["TrainingPlan"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WeaknessProfile(Base):
    """Rolling aggregate of a user's recurring mistake patterns.

    `patterns` is a JSON map like {"missed_fork": 12, "hanging_piece": 8, ...},
    incremented as games are analyzed. Recommendations are derived from the top
    entries rather than stored, so they always reflect current data.
    """

    __tablename__ = "weakness_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    patterns: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    games_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="weakness_profile")
