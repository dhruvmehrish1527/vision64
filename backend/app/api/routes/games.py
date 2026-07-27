"""Game import and full-game review endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.analysis import GameReview, Move, MoveAnalysis
from app.models.game import Game
from app.models.puzzle import Puzzle
from app.models.user import User, WeaknessProfile
from app.schemas.game import (
    GameReviewResponse,
    GameSummarySchema,
    ImportPgnRequest,
)
from app.services.chess_io import parse_pgn
from app.services.engine import EngineUnavailable, engine_service
from app.services.puzzles import generate_from_analyses
from app.services.review import ReviewService

router = APIRouter(prefix="/games", tags=["games"])


def _merge_weaknesses(db: Session, user: User, tags: dict) -> None:
    """Fold this game's weakness tags into the user's rolling profile."""
    profile = (
        db.query(WeaknessProfile).filter(WeaknessProfile.user_id == user.id).one_or_none()
    )
    if profile is None:
        profile = WeaknessProfile(user_id=user.id, patterns={}, games_analyzed=0)
        db.add(profile)
        db.flush()

    patterns = dict(profile.patterns or {})
    for tag, count in tags.items():
        patterns[tag] = patterns.get(tag, 0) + int(count)
    profile.patterns = patterns
    profile.games_analyzed += 1


@router.post("/import", response_model=GameReviewResponse)
def import_and_review(
    body: ImportPgnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameReviewResponse:
    """Import a PGN and (optionally) run a full engine + coaching review."""
    try:
        parsed = parse_pgn(body.pgn)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    game = Game(
        user_id=user.id,
        pgn=body.pgn,
        initial_fen=parsed.initial_fen,
        white=parsed.white,
        black=parsed.black,
        result=parsed.result,
        event=parsed.event,
        source="import",
    )
    db.add(game)
    db.flush()  # assign game.id

    # Persist the raw move list regardless of whether we review.
    for pm in parsed.moves:
        db.add(
            Move(
                game_id=game.id,
                ply=pm.ply,
                san=pm.san,
                uci=pm.uci,
                fen_before=pm.fen_before,
                fen_after=pm.fen_after,
                color=pm.color,
            )
        )

    if not body.review:
        db.commit()
        db.refresh(game)
        return GameReviewResponse(
            game=GameSummarySchema.model_validate(game),
            accuracy_white=0.0,
            accuracy_black=0.0,
            biggest_mistake_ply=None,
            turning_points=[],
            phases={},
            weakness_tags={},
            moves=[],
        )

    # Reuse the shared engine pool rather than spawning a second one.
    reviewer = ReviewService(engine_service, depth=body.depth)
    try:
        review = reviewer.review(parsed)
    except EngineUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Persist per-move analysis alongside the stored moves.
    stored_moves = {m.ply: m for m in game.moves}
    for rm in review.moves:
        move_row = stored_moves.get(rm.ply)
        if move_row is None:
            continue
        db.add(
            MoveAnalysis(
                move_id=move_row.id,
                eval_cp=rm.eval_cp,
                mate_in=rm.mate_in,
                best_move=rm.best_move,
                pv=rm.best_pv,  # best line — powers puzzle generation & the review UI
                classification=rm.classification,
                centipawn_loss=rm.centipawn_loss,
                tags=rm.tags,
            )
        )

    game.accuracy_white = review.accuracy_white
    game.accuracy_black = review.accuracy_black
    db.add(
        GameReview(
            game_id=game.id,
            accuracy=(review.accuracy_white + review.accuracy_black) / 2,
            biggest_mistake_ply=review.biggest_mistake_ply,
            phases={**review.phases, "turning_points": review.turning_points},
        )
    )

    _merge_weaknesses(db, user, review.weakness_tags)

    # Auto-mine this game's blunders into personalized puzzles, so the puzzle
    # pool grows every time a game is reviewed (deduped by FEN).
    for spec in generate_from_analyses(
        [
            {
                "fen_before": rm.fen_before,
                "classification": rm.classification,
                "centipawn_loss": rm.centipawn_loss,
                "best_pv": rm.best_pv,
                "tags": rm.tags,
                "rating": user.rating,
            }
            for rm in review.moves
        ]
    ):
        if db.query(Puzzle).filter(Puzzle.fen == spec["fen"]).first():
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

    db.commit()
    db.refresh(game)

    return GameReviewResponse(
        game=GameSummarySchema.model_validate(game),
        accuracy_white=review.accuracy_white,
        accuracy_black=review.accuracy_black,
        biggest_mistake_ply=review.biggest_mistake_ply,
        turning_points=review.turning_points,
        phases=review.phases,
        weakness_tags=review.weakness_tags,
        moves=[rm.__dict__ for rm in review.moves],
    )


@router.get("", response_model=list[GameSummarySchema])
def list_games(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Game]:
    """List the current user's games, newest first."""
    return (
        db.query(Game)
        .filter(Game.user_id == user.id)
        .order_by(Game.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{game_id}/review", response_model=GameReviewResponse)
def get_review(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameReviewResponse:
    """Fetch a previously stored review so a game can be reopened."""
    game = (
        db.query(Game).filter(Game.id == game_id, Game.user_id == user.id).one_or_none()
    )
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found.")

    review = game.review
    moves = []
    weakness_tags: dict[str, int] = {}
    for m in game.moves:
        a = m.analysis
        if a is None:
            continue
        for t in a.tags or []:
            weakness_tags[t] = weakness_tags.get(t, 0) + 1
        moves.append(
            {
                "ply": m.ply,
                "color": m.color,
                "san": m.san,
                "uci": m.uci,
                "fen_before": m.fen_before,
                "eval_cp": a.eval_cp,
                "mate_in": a.mate_in,
                "best_move": a.best_move,
                "best_pv": a.pv or [],
                "classification": a.classification or "Good",
                "centipawn_loss": a.centipawn_loss or 0,
                "tags": a.tags or [],
            }
        )

    phases = dict(review.phases) if review else {}
    turning_points = phases.pop("turning_points", []) if phases else []
    return GameReviewResponse(
        game=GameSummarySchema.model_validate(game),
        accuracy_white=game.accuracy_white or 0.0,
        accuracy_black=game.accuracy_black or 0.0,
        biggest_mistake_ply=review.biggest_mistake_ply if review else None,
        turning_points=turning_points,
        phases=phases,
        weakness_tags=weakness_tags,
        moves=moves,
    )
