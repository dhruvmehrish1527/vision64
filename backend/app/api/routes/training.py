"""Adaptive training plan endpoints.

`GET /training/plan` returns the active plan, generating one on first use.
`POST /training/plan/regenerate` re-plans against the *current* weakness profile
while preserving completed weeks, so the plan follows the player's progress.
`POST /training/weeks/{id}/complete` marks progress and auto-advances the plan
once everything is done.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.training import TrainingPlan, TrainingWeek
from app.models.user import User, WeaknessProfile
from app.services.training import build_plan, puzzle_theme_for_goal

router = APIRouter(prefix="/training", tags=["training"])


class WeekSchema(BaseModel):
    id: int
    week_number: int
    goal: str | None
    focus_topics: list[str]
    completed: bool
    puzzle_theme: str | None = None


class PlanSchema(BaseModel):
    id: int
    title: str
    weeks: list[WeekSchema]
    progress_percent: int


def _patterns(db: Session, user: User) -> dict[str, int]:
    profile = (
        db.query(WeaknessProfile).filter(WeaknessProfile.user_id == user.id).one_or_none()
    )
    return dict(profile.patterns) if profile and profile.patterns else {}


def _serialize(plan: TrainingPlan) -> PlanSchema:
    weeks = sorted(plan.weeks, key=lambda w: w.week_number)
    done = sum(1 for w in weeks if w.completed)
    return PlanSchema(
        id=plan.id,
        title=plan.title,
        weeks=[
            WeekSchema(
                id=w.id,
                week_number=w.week_number,
                goal=w.goal,
                focus_topics=list(w.focus_topics or []),
                completed=w.completed,
                puzzle_theme=puzzle_theme_for_goal(w.goal or ""),
            )
            for w in weeks
        ],
        progress_percent=round(100 * done / len(weeks)) if weeks else 0,
    )


def _create_plan(db: Session, user: User) -> TrainingPlan:
    plan = TrainingPlan(user_id=user.id, title="Your personalized plan", active=True)
    db.add(plan)
    db.flush()
    for pw in build_plan(_patterns(db, user)):
        db.add(
            TrainingWeek(
                plan_id=plan.id,
                week_number=pw.week_number,
                goal=pw.goal,
                focus_topics=pw.focus_topics,
            )
        )
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plan", response_model=PlanSchema)
def get_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanSchema:
    """Return the active plan, creating one on first request."""
    plan = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.user_id == user.id, TrainingPlan.active.is_(True))
        .order_by(TrainingPlan.created_at.desc())
        .first()
    )
    if plan is None:
        plan = _create_plan(db, user)
    return _serialize(plan)


@router.post("/plan/regenerate", response_model=PlanSchema)
def regenerate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanSchema:
    """Re-plan against current weaknesses, preserving completed weeks.

    Weeks the user already finished stay (progress is never lost); the remaining
    slots are refilled from the latest weakness data, so the plan adapts as the
    player improves.
    """
    plan = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.user_id == user.id, TrainingPlan.active.is_(True))
        .order_by(TrainingPlan.created_at.desc())
        .first()
    )
    if plan is None:
        return _serialize(_create_plan(db, user))

    completed = [w for w in plan.weeks if w.completed]
    completed_goals = {w.goal for w in completed}

    # Drop the unfinished weeks; they'll be replaced by fresh recommendations.
    for w in list(plan.weeks):
        if not w.completed:
            db.delete(w)
    db.flush()

    proposed = build_plan(_patterns(db, user), weeks=4 + len(completed))
    next_number = len(completed) + 1
    for pw in proposed:
        if pw.goal in completed_goals:
            continue  # already mastered — don't repeat it
        db.add(
            TrainingWeek(
                plan_id=plan.id,
                week_number=next_number,
                goal=pw.goal,
                focus_topics=pw.focus_topics,
            )
        )
        next_number += 1

    # Renumber the preserved weeks so ordering stays contiguous.
    for i, w in enumerate(sorted(completed, key=lambda x: x.week_number), start=1):
        w.week_number = i

    db.commit()
    db.refresh(plan)
    return _serialize(plan)


@router.post("/weeks/{week_id}/complete", response_model=PlanSchema)
def complete_week(
    week_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanSchema:
    """Mark a week complete (idempotent) and return the updated plan."""
    week = db.get(TrainingWeek, week_id)
    if week is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Week not found.")

    plan = db.get(TrainingPlan, week.plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Week not found.")

    week.completed = True
    db.commit()
    db.refresh(plan)
    return _serialize(plan)
