"""Model registry.

Importing this package imports every model so that `Base.metadata` is fully
populated — Alembic's autogenerate and `create_all` both rely on that.
"""

from app.models.analysis import GameReview, Move, MoveAnalysis
from app.models.game import Game
from app.models.puzzle import Puzzle, PuzzleAttempt
from app.models.repertoire import RepertoireEntry
from app.models.social import Bookmark
from app.models.training import TrainingPlan, TrainingWeek
from app.models.user import User, WeaknessProfile

__all__ = [
    "User",
    "WeaknessProfile",
    "Game",
    "Move",
    "MoveAnalysis",
    "GameReview",
    "TrainingPlan",
    "TrainingWeek",
    "Puzzle",
    "PuzzleAttempt",
    "RepertoireEntry",
    "Bookmark",
]
