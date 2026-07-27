"""Analysis and coaching endpoints.

These compose the engine, classifier, and coach so a bare "best move" is never
returned without the option of an explanation.
"""

from __future__ import annotations

import json

import chess
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.clerk import get_current_user
from app.models.user import User
from app.schemas.analysis import (
    EngineSchema,
    ExplainMoveRequest,
    ExplainMoveResponse,
    ExplainPositionRequest,
    PositionRequest,
    PositionResponse,
)
from app.services.chess_io import uci_line_to_san, validate_fen
from app.services.classifier import classify_move
from app.services.coach import CoachUnavailable, coach_service
from app.services.engine import EngineUnavailable, engine_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _sse(data: str, event: str | None = None) -> str:
    """Format a Server-Sent Events frame."""
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {data}\n\n"


def _engine_or_503(fn, *args, **kwargs):
    """Run an engine call, translating a missing engine into a clean 503."""
    try:
        return fn(*args, **kwargs)
    except EngineUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ValueError as exc:  # illegal FEN
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/position", response_model=PositionResponse)
def analyse_position(
    body: PositionRequest,
    _user: User = Depends(get_current_user),
) -> PositionResponse:
    """Analyse a position: eval bar, best move, top-N candidates, PV, depth.

    With `explain=true`, also returns a coaching explanation of the plan.
    """
    if not validate_fen(body.fen):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal FEN.")

    result = _engine_or_503(
        engine_service.analyse, body.fen, multipv=body.multipv, depth=body.depth
    )

    explanation: str | None = None
    if body.explain:
        try:
            explanation = coach_service.explain_position(
                fen=body.fen, rating=body.rating, engine=result.to_dict()
            )
        except CoachUnavailable as exc:
            # The board must stay usable even if the coach is down.
            explanation = f"(Coach unavailable: {exc})"

    return PositionResponse(engine=EngineSchema(**result.to_dict()), explanation=explanation)


@router.post("/explain-move", response_model=ExplainMoveResponse)
def explain_move(
    body: ExplainMoveRequest,
    _user: User = Depends(get_current_user),
) -> ExplainMoveResponse:
    """Classify a played move and explain why it earned that label."""
    if not validate_fen(body.fen_before):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal FEN.")

    board_before = chess.Board(body.fen_before)
    try:
        move = chess.Move.from_uci(body.move_uci)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed UCI move.") from exc
    if move not in board_before.legal_moves:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal move for this position.")

    played_san = board_before.san(move)
    board_after = board_before.copy()
    board_after.push(move)

    before = _engine_or_503(engine_service.analyse, body.fen_before, multipv=1)
    after = _engine_or_503(engine_service.analyse, board_after.fen(), multipv=1)

    result = classify_move(
        board_before=board_before,
        move=move,
        eval_before_white=before.eval_cp,
        mate_before=before.mate_in,
        eval_after_white=after.eval_cp,
        mate_after=after.mate_in,
        best_move_uci=before.best_move,
        best_reply_uci=after.best_move,
    )

    try:
        explanation = coach_service.explain_move(
            fen_before=body.fen_before,
            played_san=played_san,
            rating=body.rating,
            eval_cp=after.eval_cp,
            mate_in=after.mate_in,
            best_move_san=before.best_move_san,
            classification=result.classification.value,
            tags=result.tags,
            pv_san=uci_line_to_san(body.fen_before, before.pv),
        )
    except CoachUnavailable as exc:
        explanation = f"(Coach unavailable: {exc})"

    return ExplainMoveResponse(
        engine=EngineSchema(**after.to_dict()),
        classification=result.to_dict(),
        explanation=explanation,
    )


@router.post("/explain-position")
def explain_position(
    body: ExplainPositionRequest,
    _user: User = Depends(get_current_user),
) -> dict:
    """Return just a coaching explanation for a position (no candidate list)."""
    if not validate_fen(body.fen):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal FEN.")
    result = _engine_or_503(engine_service.analyse, body.fen, multipv=1, depth=body.depth)
    try:
        explanation = coach_service.explain_position(
            fen=body.fen, rating=body.rating, engine=result.to_dict()
        )
    except CoachUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return {"explanation": explanation, "engine": result.to_dict()}


@router.post("/explain-move/stream")
def explain_move_stream(
    body: ExplainMoveRequest,
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a move classification then a token-by-token coaching explanation.

    The first SSE frame carries the deterministic classification (event: meta),
    then explanation text streams in `message` frames, ending with `done`.
    """
    if not validate_fen(body.fen_before):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal FEN.")
    board_before = chess.Board(body.fen_before)
    try:
        move = chess.Move.from_uci(body.move_uci)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed UCI move.") from exc
    if move not in board_before.legal_moves:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal move.")

    played_san = board_before.san(move)
    board_after = board_before.copy()
    board_after.push(move)

    before = _engine_or_503(engine_service.analyse, body.fen_before, multipv=1)
    after = _engine_or_503(engine_service.analyse, board_after.fen(), multipv=1)
    classification = classify_move(
        board_before=board_before,
        move=move,
        eval_before_white=before.eval_cp,
        mate_before=before.mate_in,
        eval_after_white=after.eval_cp,
        mate_after=after.mate_in,
        best_move_uci=before.best_move,
        best_reply_uci=after.best_move,
    )

    def generate():
        yield _sse(json.dumps(classification.to_dict()), event="meta")
        try:
            for chunk in coach_service.stream_move(
                fen_before=body.fen_before,
                played_san=played_san,
                rating=body.rating,
                eval_cp=after.eval_cp,
                mate_in=after.mate_in,
                best_move_san=before.best_move_san,
                classification=classification.classification.value,
                tags=classification.tags,
                pv_san=uci_line_to_san(body.fen_before, before.pv),
            ):
                yield _sse(json.dumps(chunk))
        except CoachUnavailable as exc:
            yield _sse(json.dumps(str(exc)), event="error")
        yield _sse("[DONE]", event="done")

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/explain-position/stream")
def explain_position_stream(
    body: ExplainPositionRequest,
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a coaching explanation of a position token-by-token."""
    if not validate_fen(body.fen):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Illegal FEN.")
    result = _engine_or_503(engine_service.analyse, body.fen, multipv=1, depth=body.depth)

    def generate():
        try:
            for chunk in coach_service.stream_position(
                fen=body.fen, rating=body.rating, engine=result.to_dict()
            ):
                yield _sse(json.dumps(chunk))
        except CoachUnavailable as exc:
            yield _sse(json.dumps(str(exc)), event="error")
        yield _sse("[DONE]", event="done")

    return StreamingResponse(generate(), media_type="text/event-stream")
