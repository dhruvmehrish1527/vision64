"""Tactical puzzles and per-user attempts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, utcnow


class Puzzle(Base):
    """A tactic: a position plus the correct move sequence."""

    __tablename__ = "puzzles"

    fen: Mapped[str] = mapped_column(String(120), nullable=False)
    solution_uci: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    # "fork" | "pin" | "skewer" | "mate_in_1".."mate_in_5" | "endgame" | ...
    theme: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="generated", nullable=False)

    attempts: Mapped[list["PuzzleAttempt"]] = relationship(
        back_populates="puzzle", cascade="all, delete-orphan"
    )


class PuzzleAttempt(Base):
    """One user's attempt at a puzzle — powers puzzle-rating and accuracy trends."""

    __tablename__ = "puzzle_attempts"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    puzzle_id: Mapped[int] = mapped_column(
        ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    puzzle: Mapped["Puzzle"] = relationship(back_populates="attempts")
