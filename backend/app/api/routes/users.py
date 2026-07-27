"""User profile, dashboard, and weakness-driven recommendations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.game import Game
from app.models.puzzle import PuzzleAttempt
from app.models.user import User, WeaknessProfile
from app.schemas.game import UserSchema

router = APIRouter(prefix="/users", tags=["users"])

# Human-readable advice keyed by the tags the classifier emits.
RECOMMENDATIONS = {
    "missed_fork": "You frequently miss knight and queen forks. Drill fork puzzles.",
    "hanging_piece": "You leave pieces undefended. Before each move, check what your "
                     "opponent can capture for free.",
    "missed_mate": "You miss forced mates. Practice mate-in-1 to mate-in-3 puzzles.",
    "missed_win": "You let winning positions slip. Slow down when you're ahead and "
                  "convert carefully.",
    "blundered_material": "You drop material under pressure. Do a blunder-check on "
                          "every move: is anything hanging?",
}


@router.get("/me", response_model=UserSchema)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/me/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Aggregate everything the dashboard shows."""
    games_analyzed = db.query(func.count(Game.id)).filter(Game.user_id == user.id).scalar() or 0

    puzzle_total = (
        db.query(func.count(PuzzleAttempt.id))
        .filter(PuzzleAttempt.user_id == user.id)
        .scalar()
        or 0
    )
    puzzle_correct = (
        db.query(func.count(PuzzleAttempt.id))
        .filter(PuzzleAttempt.user_id == user.id, PuzzleAttempt.correct.is_(True))
        .scalar()
        or 0
    )

    avg_accuracy = (
        db.query(func.avg(Game.accuracy_white))
        .filter(Game.user_id == user.id, Game.accuracy_white.isnot(None))
        .scalar()
    )

    return {
        "rating": user.rating,
        "puzzle_rating": user.puzzle_rating,
        "streak_days": user.streak_days,
        "training_minutes": round(user.training_seconds / 60),
        "games_analyzed": games_analyzed,
        "puzzle_accuracy": round(100 * puzzle_correct / puzzle_total, 1) if puzzle_total else None,
        "average_accuracy": round(avg_accuracy, 1) if avg_accuracy else None,
        "top_weaknesses": _top_weaknesses(db, user),
    }


@router.get("/me/accuracy-trend")
def accuracy_trend(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Accuracy per reviewed game, oldest → newest, for the trend chart.

    Reports the accuracy of the side the user played where we can tell (AI games
    record the player as "You"); otherwise it falls back to White's.
    """
    games = (
        db.query(Game)
        .filter(Game.user_id == user.id, Game.accuracy_white.isnot(None))
        .order_by(Game.created_at.desc())
        .limit(limit)
        .all()
    )
    series = []
    for g in reversed(games):  # chronological for plotting
        played_black = g.black == "You"
        accuracy = g.accuracy_black if played_black else g.accuracy_white
        if accuracy is None:
            continue
        series.append(
            {
                "game_id": g.id,
                "date": g.created_at.isoformat(),
                "accuracy": round(accuracy, 1),
                "source": g.source,
            }
        )
    return series


@router.get("/me/weaknesses")
def weaknesses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Return the user's weakness tally plus personalized recommendations."""
    profile = (
        db.query(WeaknessProfile).filter(WeaknessProfile.user_id == user.id).one_or_none()
    )
    patterns = dict(profile.patterns) if profile else {}
    ranked = sorted(patterns.items(), key=lambda kv: kv[1], reverse=True)

    recommendations = [
        {"pattern": tag, "count": count, "advice": RECOMMENDATIONS.get(tag)}
        for tag, count in ranked
        if RECOMMENDATIONS.get(tag)
    ]
    return {
        "games_analyzed": profile.games_analyzed if profile else 0,
        "patterns": patterns,
        "recommendations": recommendations,
    }


def _top_weaknesses(db: Session, user: User, limit: int = 3) -> list[dict]:
    profile = (
        db.query(WeaknessProfile).filter(WeaknessProfile.user_id == user.id).one_or_none()
    )
    if not profile or not profile.patterns:
        return []
    ranked = sorted(profile.patterns.items(), key=lambda kv: kv[1], reverse=True)
    return [{"pattern": tag, "count": count} for tag, count in ranked[:limit]]
