"""A game or analysis session belonging to a user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import GameReview, Move
    from app.models.user import User

# Standard starting position.
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class Game(Base):
    """An imported PGN, a pasted game, or a fresh analysis board session."""

    __tablename__ = "games"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    pgn: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_fen: Mapped[str] = mapped_column(String(120), default=START_FEN, nullable=False)

    white: Mapped[str | None] = mapped_column(String(120), nullable=True)
    black: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # "1-0", "0-1", "1/2-1/2"
    event: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # "import" | "paste" | "board" | "ai_game" | "famous"
    source: Mapped[str] = mapped_column(String(32), default="board", nullable=False)

    # Filled after review.
    accuracy_white: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_black: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="games")
    moves: Mapped[list["Move"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Move.ply",
    )
    review: Mapped["GameReview | None"] = relationship(
        back_populates="game", uselist=False, cascade="all, delete-orphan"
    )
