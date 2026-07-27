"""Adaptive training plans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType

if TYPE_CHECKING:
    from app.models.user import User


class TrainingPlan(Base):
    """A multi-week improvement plan generated from a user's weaknesses."""

    __tablename__ = "training_plans"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Personalized plan", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="training_plans")
    weeks: Mapped[list["TrainingWeek"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="TrainingWeek.week_number",
    )


class TrainingWeek(Base):
    """One week of a plan: a set of focus topics, marked complete over time."""

    __tablename__ = "training_weeks"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    focus_topics: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="weeks")
