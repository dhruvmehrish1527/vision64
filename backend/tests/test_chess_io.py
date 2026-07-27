"""Tests for PGN/FEN parsing helpers."""

from __future__ import annotations

from app.services.chess_io import parse_pgn, uci_line_to_san, validate_fen

SCHOLARS_MATE = """\
[Event "Casual"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0
"""


def test_validate_fen():
    assert validate_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert not validate_fen("not a fen")


def test_parse_pgn_extracts_moves_and_headers():
    game = parse_pgn(SCHOLARS_MATE)
    assert game.white == "Alice"
    assert game.result == "1-0"
    assert len(game.moves) == 7  # 4 white + 3 black half-moves
    assert game.moves[0].san == "e4"
    assert game.moves[0].color == "white"
    assert game.moves[-1].san == "Qxf7#"


def test_uci_line_to_san_roundtrips():
    start = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    san = uci_line_to_san(start, ["e2e4", "e7e5", "g1f3"])
    assert san == ["e4", "e5", "Nf3"]


def test_parse_pgn_rejects_empty():
    try:
        parse_pgn("")
        assert False, "expected ValueError"
    except ValueError:
        pass
