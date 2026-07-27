"""Unit tests for AI-opponent helpers (pure functions, no engine needed)."""

from __future__ import annotations

import chess

from app.services.ai_game import LEVELS, build_pgn, game_status, get_level


def test_levels_cover_all_four_strengths():
    assert set(LEVELS) == {"beginner", "intermediate", "advanced", "master"}
    # Elo increases monotonically with difficulty.
    elos = [LEVELS[k].elo for k in ["beginner", "intermediate", "advanced", "master"]]
    assert elos == sorted(elos)


def test_get_level_falls_back_to_default():
    assert get_level(None).key == "intermediate"
    assert get_level("nonsense").key == "intermediate"
    assert get_level("MASTER").key == "master"


def test_game_status_detects_checkmate_winner():
    # Fool's mate: White is checkmated, so Black wins.
    board = chess.Board()
    for san in ["f3", "e5", "g4", "Qh4#"]:
        board.push_san(san)
    status, result = game_status(board)
    assert status == "checkmate"
    assert result == "0-1"


def test_game_status_in_progress_at_start():
    assert game_status(chess.Board()) == ("in_progress", None)


def test_game_status_stalemate():
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    status, result = game_status(board)
    assert status == "stalemate"
    assert result == "1/2-1/2"


def test_build_pgn_is_parseable():
    from app.services.chess_io import parse_pgn

    pgn = build_pgn(["e4", "e5", "Nf3"], white="You", black="AI", result="*")
    parsed = parse_pgn(pgn)
    assert [m.san for m in parsed.moves] == ["e4", "e5", "Nf3"]
    assert parsed.white == "You"
