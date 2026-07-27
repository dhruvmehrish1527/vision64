"""Idempotent puzzle seeding.

On startup, if the puzzle table is empty and Stockfish is available, we turn the
curated tactical FENs into real puzzles by letting the engine compute each
solution. This guarantees the seed puzzles are correct and gives the trainer
something to serve before any game has been reviewed. If the engine isn't
installed, seeding is skipped silently — the app still runs.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.puzzle import Puzzle
from app.services.engine import EngineUnavailable, engine_service
from app.services.puzzles import CURATED_FENS, build_from_fen

logger = get_logger(__name__)


def seed_puzzles(db: Session) -> int:
    """Seed curated puzzles once. Returns how many were created."""
    existing = db.query(func.count(Puzzle.id)).scalar() or 0
    if existing > 0:
        return 0

    created = 0
    for fen, theme_hint in CURATED_FENS:
        try:
            spec = build_from_fen(engine_service, fen, rating=1100, theme_hint=theme_hint)
        except EngineUnavailable:
            logger.info("Stockfish unavailable; skipping puzzle seeding.")
            return created
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not seed puzzle from %s: %s", fen, exc)
            continue
        if spec is None:
            continue
        db.add(
            Puzzle(
                fen=spec["fen"],
                solution_uci=spec["solution_uci"],
                theme=spec["theme"],
                rating=spec["rating"],
                source="curated",
            )
        )
        created += 1

    if created:
        db.commit()
        logger.info("Seeded %d curated puzzles.", created)
    return created
