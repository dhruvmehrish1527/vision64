"""Saved opening repertoire entries."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RepertoireEntry(Base):
    """An opening a user has saved to study, for White or for Black."""

    __tablename__ = "repertoire_entries"
    # A user saves a given opening once per colour.
    __table_args__ = (
        UniqueConstraint("user_id", "eco", "color", name="uq_repertoire_user_eco_color"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eco: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    color: Mapped[str] = mapped_column(String(5), nullable=False)  # "white" | "black"
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
