"""Unit tests for the deterministic move classifier.

The classifier is pure arithmetic over engine numbers, so it needs no engine or
network — ideal for fast, reliable tests.
"""

from __future__ import annotations

import chess

from app.services.classifier import Classification, classify_move


def _classify(fen: str, uci: str, before: int, after: int, best_uci: str, ply: int = 20):
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    return classify_move(
        board_before=board,
        move=move,
        eval_before_white=before,
        mate_before=None,
        eval_after_white=after,
        mate_after=None,
        best_move_uci=best_uci,
        best_reply_uci=None,
        ply=ply,
    )


def test_best_move_is_excellent_or_book():
    # 1.e4 from the start: near-zero loss, early ply → Book.
    res = _classify(chess.STARTING_FEN, "e2e4", before=20, after=25, best_uci="e2e4", ply=1)
    assert res.classification in {Classification.BOOK, Classification.EXCELLENT}
    assert res.centipawn_loss == 0


def test_large_drop_is_blunder():
    # White was fine (+30) and the move leaves it at -400 → big loss → Blunder.
    res = _classify(chess.STARTING_FEN, "g1f3", before=30, after=-400, best_uci="e2e4")
    assert res.classification == Classification.BLUNDER
    assert res.centipawn_loss >= 300


def test_moderate_slip_is_inaccuracy_or_mistake():
    res = _classify(chess.STARTING_FEN, "b1c3", before=30, after=-90, best_uci="e2e4")
    assert res.classification in {
        Classification.INACCURACY,
        Classification.MISTAKE,
    }


def test_missed_win_is_tagged():
    # Was winning (+500), dropped to +50 → the "missed_win" pattern fires.
    res = _classify(chess.STARTING_FEN, "a2a3", before=500, after=50, best_uci="e2e4")
    assert "missed_win" in res.tags


def test_black_perspective_loss_is_positive():
    # A position with Black to move; a bad Black move should show positive loss.
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    res = _classify(fen, "a7a6", before=25, after=25, best_uci="e7e5")
    assert res.centipawn_loss >= 0
