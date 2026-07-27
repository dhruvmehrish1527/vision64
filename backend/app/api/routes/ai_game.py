"""AI opponent endpoints.

Play a full game against Stockfish at an adjustable strength. State lives in the
database (a `Game` plus its `Move` rows) rather than in memory, so a game
survives restarts, works across devices, and — because it's stored in exactly
the same shape as an imported PGN — can be fed straight into the existing review
pipeline for post-game coaching.
"""

from __future__ import annotations

import chess
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.analysis import Move
from app.models.game import Game
from app.models.user import User
from app.schemas.ai_game import (
    AiGameState,
    GameFeedback,
    LevelSchema,
    NewGameRequest,
    PlayMoveRequest,
)
from app.services.ai_game import LEVELS, build_pgn, game_status, get_level
from app.services.engine import EngineUnavailable, engine_service
from app.services.review import ReviewService

router = APIRouter(prefix="/ai", tags=["ai-opponent"])

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _load_game(db: Session, game_id: int, user: User) -> Game:
    game = (
        db.query(Game).filter(Game.id == game_id, Game.user_id == user.id).one_or_none()
    )
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found.")
    if game.source != "ai_game":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not an AI game.")
    return game


def _replay(game: Game) -> tuple[chess.Board, list[str]]:
    """Rebuild the board from stored moves (single source of truth)."""
    board = chess.Board(game.initial_fen or START_FEN)
    san: list[str] = []
    for m in sorted(game.moves, key=lambda x: x.ply):
        move = chess.Move.from_uci(m.uci)
        san.append(board.san(move))
        board.push(move)
    return board, san


def _record(db: Session, game: Game, board_before: chess.Board, move: chess.Move) -> None:
    """Append one half-move to the game. Caller commits and refreshes."""
    after = board_before.copy()
    after.push(move)
    db.add(
        Move(
            game_id=game.id,
            ply=len(game.moves) + 1,
            san=board_before.san(move),
            uci=move.uci(),
            fen_before=board_before.fen(),
            fen_after=after.fen(),
            color="white" if board_before.turn == chess.WHITE else "black",
        )
    )


def _state(game: Game, board: chess.Board, san: list[str], last_ai_uci: str | None) -> AiGameState:
    st, result = game_status(board)
    player_is_white = game.white == "You"
    your_turn = (board.turn == chess.WHITE) == player_is_white
    return AiGameState(
        game_id=game.id,
        fen=board.fen(),
        status=st,
        result=result,
        player_color="white" if player_is_white else "black",
        level=game.event or "intermediate",
        moves_san=san,
        last_move_uci=last_ai_uci,
        your_turn=your_turn and st == "in_progress",
    )


@router.get("/levels", response_model=list[LevelSchema])
def levels() -> list[LevelSchema]:
    """List the available opponent strengths."""
    return [
        LevelSchema(key=l.key, label=l.label, elo=l.elo, blurb=l.blurb)
        for l in LEVELS.values()
    ]


@router.post("/games", response_model=AiGameState)
def new_game(
    body: NewGameRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiGameState:
    """Start a new game against the AI. If the player is Black, the AI opens."""
    level = get_level(body.level)
    player_white = body.play_as.lower() != "black"

    game = Game(
        user_id=user.id,
        initial_fen=START_FEN,
        white="You" if player_white else f"Vision64 {level.label}",
        black=f"Vision64 {level.label}" if player_white else "You",
        event=level.key,          # stores the difficulty for later turns
        source="ai_game",
    )
    db.add(game)
    db.flush()

    board = chess.Board(START_FEN)
    last_ai: str | None = None

    # AI moves first when the player chose Black.
    if not player_white:
        try:
            uci = engine_service.play_move(
                board.fen(), elo=level.elo, movetime_ms=level.movetime_ms
            )
        except EngineUnavailable as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        if uci:
            move = chess.Move.from_uci(uci)
            _record(db, game, board, move)
            board.push(move)
            last_ai = uci

    db.commit()
    db.refresh(game)
    _, san = _replay(game)
    return _state(game, board, san, last_ai)


@router.post("/games/{game_id}/move", response_model=AiGameState)
def play_move(
    game_id: int,
    body: PlayMoveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiGameState:
    """Play the player's move, then have the AI reply."""
    game = _load_game(db, game_id, user)
    board, _ = _replay(game)

    st, _ = game_status(board)
    if st != "in_progress":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This game is already over.")

    try:
        move = chess.Move.from_uci(body.uci)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed UCI move.") from exc
    if move not in board.legal_moves:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal move.")

    _record(db, game, board, move)
    board.push(move)
    db.commit()
    db.refresh(game)

    # AI replies unless the player's move ended the game.
    last_ai: str | None = None
    st, result = game_status(board)
    if st == "in_progress":
        level = get_level(game.event)
        try:
            uci = engine_service.play_move(
                board.fen(), elo=level.elo, movetime_ms=level.movetime_ms
            )
        except EngineUnavailable as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        if uci:
            ai_move = chess.Move.from_uci(uci)
            _record(db, game, board, ai_move)
            board.push(ai_move)
            last_ai = uci
        db.commit()
        db.refresh(game)

    # Persist the final result once the game ends.
    st, result = game_status(board)
    if st != "in_progress" and not game.result:
        game.result = result
        db.commit()
        db.refresh(game)

    _, san = _replay(game)
    return _state(game, board, san, last_ai)


@router.get("/games/{game_id}", response_model=AiGameState)
def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiGameState:
    """Resume an in-progress AI game."""
    game = _load_game(db, game_id, user)
    board, san = _replay(game)
    return _state(game, board, san, None)


@router.post("/games/{game_id}/feedback", response_model=GameFeedback)
def game_feedback(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameFeedback:
    """Run the review pipeline over a finished AI game and coach the player.

    Reuses the exact same engine + classifier path as PGN review — the AI game is
    just another game — and reports accuracy from the player's own side.
    """
    game = _load_game(db, game_id, user)
    board, san = _replay(game)
    if not san:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No moves to review yet.")

    st, result = game_status(board)
    pgn = build_pgn(san, white=game.white or "You", black=game.black or "AI", result=result)

    from app.services.chess_io import parse_pgn

    reviewer = ReviewService(engine_service, depth=12)
    try:
        review = reviewer.review(parse_pgn(pgn))
    except EngineUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    player_white = game.white == "You"
    accuracy = review.accuracy_white if player_white else review.accuracy_black

    # Only count the player's own mistakes toward their feedback.
    player_color = "white" if player_white else "black"
    own_tags: dict[str, int] = {}
    for m in review.moves:
        if m.color != player_color:
            continue
        for t in m.tags:
            own_tags[t] = own_tags.get(t, 0) + 1

    outcome = {
        "checkmate": "You won!" if (result == "1-0") == player_white else "You were checkmated.",
        "stalemate": "The game ended in stalemate.",
        "draw": "The game ended in a draw.",
        "in_progress": "Game still in progress.",
    }.get(st, "Game over.")

    top = sorted(own_tags.items(), key=lambda kv: kv[1], reverse=True)
    leak = f" Your most frequent issue was {top[0][0].replace('_', ' ')}." if top else ""
    summary = f"{outcome} You played at {accuracy}% accuracy.{leak}"

    game.accuracy_white = review.accuracy_white
    game.accuracy_black = review.accuracy_black
    db.commit()

    return GameFeedback(
        accuracy=accuracy,
        summary=summary,
        biggest_mistake_ply=review.biggest_mistake_ply,
        weakness_tags=own_tags,
    )
