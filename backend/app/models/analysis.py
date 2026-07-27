"""Per-move engine analysis, classification, and whole-game review."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType

if TYPE_CHECKING:
    from app.models.game import Game


class Move(Base):
    """A single half-move (ply) within a game."""

    __tablename__ = "moves"

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ply: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-indexed half-move number
    san: Mapped[str] = mapped_column(String(16), nullable=False)  # "Nf3"
    uci: Mapped[str] = mapped_column(String(8), nullable=False)   # "g1f3"
    fen_before: Mapped[str] = mapped_column(String(120), nullable=False)
    fen_after: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(5), nullable=False)  # "white" | "black"

    game: Mapped["Game"] = relationship(back_populates="moves")
    analysis: Mapped["MoveAnalysis | None"] = relationship(
        back_populates="move", uselist=False, cascade="all, delete-orphan"
    )


class MoveAnalysis(Base):
    """Engine evaluation + deterministic classification for one move.

    `explanation` is nullable and filled lazily — only when the coach is asked,
    so we never pay for LLM tokens we don't show.
    """

    __tablename__ = "move_analyses"

    move_id: Mapped[int] = mapped_column(
        ForeignKey("moves.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )

    # Evaluation of the position AFTER the move, from White's perspective (centipawns).
    eval_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate_in: Mapped[int | None] = mapped_column(Integer, nullable=True)  # +N = mate for side to move
    best_move: Mapped[str | None] = mapped_column(String(8), nullable=True)  # UCI of best reply
    pv: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)  # principal variation (UCI list)
    depth: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Deterministic label + how much the move lost vs. best (centipawns).
    classification: Mapped[str | None] = mapped_column(String(16), nullable=True)
    centipawn_loss: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)  # ["missed_fork", ...]

    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    move: Mapped["Move"] = relationship(back_populates="analysis")


class GameReview(Base):
    """A coaching report for an entire game."""

    __tablename__ = "game_reviews"

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )

    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    biggest_mistake_ply: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # {"opening": {...}, "middlegame": {...}, "endgame": {...}, "turning_points": [...]}
    phases: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="review")
