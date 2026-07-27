"""Puzzle trainer endpoints.

Interactive, leak-free solving: the client is served a puzzle *without* the
solution and submits one move at a time. The backend validates each move against
the stored line, auto-plays the opponent's reply, and only reveals the full
solution once the attempt ends (solved or failed). Attempts update a Glicko-lite
puzzle rating and the daily streak.
"""

from __future__ import annotations

import math
from datetime import timedelta

import chess
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.base import utcnow
from app.db.session import get_db
from app.models.game import Game
from app.models.puzzle import Puzzle, PuzzleAttempt
from app.models.user import User, WeaknessProfile
from app.schemas.puzzle import (
    GenerateFromGameRequest,
    GenerateResponse,
    PuzzleMoveRequest,
    PuzzleMoveResponse,
    PuzzleSchema,
)
from app.services.engine import EngineService
from app.services.puzzles import TAG_TO_THEME, generate_from_analyses

router = APIRouter(prefix="/puzzles", tags=["puzzles"])

ELO_K = 24


def _player_move_count(solution: list[str]) -> int:
    # Solution alternates player, opponent, player, ... starting with the solver.
    return math.ceil(len(solution) / 2)


def _to_schema(p: Puzzle) -> PuzzleSchema:
    board = chess.Board(p.fen)
    return PuzzleSchema(
        id=p.id,
        fen=p.fen,
        theme=p.theme,
        rating=p.rating,
        side_to_move="white" if board.turn == chess.WHITE else "black",
        player_move_count=_player_move_count(p.solution_uci),
    )


def _preferred_theme(db: Session, user: User) -> str | None:
    """Pick a theme that trains the user's single biggest weakness, if any."""
    profile = (
        db.query(WeaknessProfile).filter(WeaknessProfile.user_id == user.id).one_or_none()
    )
    if not profile or not profile.patterns:
        return None
    for tag, _ in sorted(profile.patterns.items(), key=lambda kv: kv[1], reverse=True):
        if tag in TAG_TO_THEME:
            return TAG_TO_THEME[tag]
    return None


@router.get("/next", response_model=PuzzleSchema)
def next_puzzle(
    theme: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PuzzleSchema:
    """Serve the next puzzle — weakness-targeted unless a theme is requested."""
    target_theme = theme or _preferred_theme(db, user)
    low, high = user.puzzle_rating - 400, user.puzzle_rating + 400

    def pick(with_theme: bool, with_rating: bool) -> Puzzle | None:
        q = db.query(Puzzle)
        if with_theme and target_theme:
            q = q.filter(Puzzle.theme == target_theme)
        if with_rating:
            q = q.filter(Puzzle.rating >= low, Puzzle.rating <= high)
        return q.order_by(func.random()).first()

    # Prefer theme+rating, then relax constraints so we always return something.
    puzzle = pick(True, True) or pick(True, False) or pick(False, True) or pick(False, False)
    if puzzle is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No puzzles available yet. Review a game to generate personalized ones.",
        )
    return _to_schema(puzzle)


@router.post("/{puzzle_id}/move", response_model=PuzzleMoveResponse)
def submit_move(
    puzzle_id: int,
    body: PuzzleMoveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PuzzleMoveResponse:
    """Validate one solver move; auto-play the reply; finish when solved/failed."""
    puzzle = db.get(Puzzle, puzzle_id)
    if puzzle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Puzzle not found.")

    solution = puzzle.solution_uci
    idx = body.player_move_index * 2
    if idx >= len(solution):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Move index past the solution.")

    correct = body.uci == solution[idx]

    if not correct:
        _record_attempt(db, user, puzzle, correct=False, time_ms=body.time_ms)
        db.commit()
        return PuzzleMoveResponse(correct=False, solved=False, solution_uci=solution)

    reply_idx = idx + 1
    opponent_reply = solution[reply_idx] if reply_idx < len(solution) else None
    solved = (idx + 2) >= len(solution)  # no further solver move remains

    new_rating = None
    if solved:
        new_rating = _record_attempt(db, user, puzzle, correct=True, time_ms=body.time_ms)
    db.commit()

    return PuzzleMoveResponse(
        correct=True,
        solved=solved,
        opponent_reply_uci=opponent_reply,
        new_puzzle_rating=new_rating,
    )


@router.post("/generate-from-game", response_model=GenerateResponse)
def generate_from_game(
    body: GenerateFromGameRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerateResponse:
    """Mine a reviewed game's blunders into personalized puzzles."""
    game = (
        db.query(Game).filter(Game.id == body.game_id, Game.user_id == user.id).one_or_none()
    )
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found.")

    rows = []
    for m in game.moves:
        a = m.analysis
        if a is None:
            continue
        rows.append(
            {
                "fen_before": m.fen_before,
                "classification": a.classification,
                "centipawn_loss": a.centipawn_loss,
                "best_pv": a.pv or [],
                "tags": a.tags or [],
                "rating": user.rating,
            }
        )

    created = 0
    for spec in generate_from_analyses(rows):
        # Skip duplicates by FEN.
        exists = db.query(Puzzle).filter(Puzzle.fen == spec["fen"]).first()
        if exists:
            continue
        db.add(
            Puzzle(
                fen=spec["fen"],
                solution_uci=spec["solution_uci"],
                theme=spec["theme"],
                rating=spec["rating"],
                source="from_game",
            )
        )
        created += 1
    db.commit()
    return GenerateResponse(created=created)


def _record_attempt(
    db: Session, user: User, puzzle: Puzzle, *, correct: bool, time_ms: int | None
) -> int:
    """Persist the attempt, update the Elo-style puzzle rating and streak."""
    db.add(
        PuzzleAttempt(
            user_id=user.id, puzzle_id=puzzle.id, correct=correct, time_ms=time_ms
        )
    )

    expected = 1 / (1 + 10 ** ((puzzle.rating - user.puzzle_rating) / 400))
    score = 1.0 if correct else 0.0
    user.puzzle_rating = max(400, round(user.puzzle_rating + ELO_K * (score - expected)))

    # Daily streak: advance if the last activity was yesterday, reset if older.
    now = utcnow()
    last = user.last_active
    if last is not None:
        gap = (now.date() - last.date()).days
        if gap == 1:
            user.streak_days += 1
        elif gap > 1:
            user.streak_days = 1
        elif user.streak_days == 0:
            user.streak_days = 1
    else:
        user.streak_days = 1
    user.last_active = now
    if time_ms:
        user.training_seconds += round(time_ms / 1000)

    return user.puzzle_rating
