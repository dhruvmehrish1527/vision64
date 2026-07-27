"""PGN / FEN parsing helpers.

Isolates all `python-chess` I/O so the route handlers stay thin. Everything
here is pure (no DB, no engine) and easily unit-tested.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import chess
import chess.pgn


@dataclass
class ParsedMove:
    ply: int
    san: str
    uci: str
    fen_before: str
    fen_after: str
    color: str  # "white" | "black"


@dataclass
class ParsedGame:
    initial_fen: str
    white: str | None
    black: str | None
    result: str | None
    event: str | None
    moves: list[ParsedMove]


def validate_fen(fen: str) -> bool:
    try:
        chess.Board(fen)
        return True
    except ValueError:
        return False


def parse_pgn(pgn_text: str) -> ParsedGame:
    """Parse a single PGN game into a flat, replayable move list.

    Raises ValueError if the PGN contains no readable game.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("No game found in the provided PGN.")

    board = game.board()
    initial_fen = board.fen()
    moves: list[ParsedMove] = []

    for ply, move in enumerate(game.mainline_moves(), start=1):
        fen_before = board.fen()
        color = "white" if board.turn == chess.WHITE else "black"
        san = board.san(move)
        board.push(move)
        moves.append(
            ParsedMove(
                ply=ply,
                san=san,
                uci=move.uci(),
                fen_before=fen_before,
                fen_after=board.fen(),
                color=color,
            )
        )

    headers = game.headers
    return ParsedGame(
        initial_fen=initial_fen,
        white=headers.get("White"),
        black=headers.get("Black"),
        result=headers.get("Result"),
        event=headers.get("Event"),
        moves=moves,
    )


def uci_line_to_san(fen: str, uci_moves: list[str], limit: int = 6) -> list[str]:
    """Convert a UCI principal variation into readable SAN for display/coaching."""
    board = chess.Board(fen)
    san: list[str] = []
    for uci in uci_moves[:limit]:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            break
        if move not in board.legal_moves:
            break
        san.append(board.san(move))
        board.push(move)
    return san
