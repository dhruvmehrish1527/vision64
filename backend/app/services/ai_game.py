"""AI opponent: difficulty levels and game-state helpers.

Four named strengths map to Stockfish `UCI_Elo` targets plus a thinking time.
We deliberately use the engine's own strength limiter rather than a shallow
search: at low Elo Stockfish makes *plausible human mistakes* (hanging a piece,
missing a tactic), which is what makes it a useful sparring partner — a
shallow-search bot instead plays alien, random-looking moves.

The game itself is stored as a `Game` row plus its `Move` rows, so an AI game is
the same shape as an imported PGN and can be reviewed by the existing pipeline
with no special-casing.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class Level:
    key: str
    label: str
    elo: int
    movetime_ms: int
    blurb: str


LEVELS: dict[str, Level] = {
    "beginner": Level(
        "beginner", "Beginner", 1320, 200,
        "Plays natural moves but misses tactics — a friendly first opponent.",
    ),
    "intermediate": Level(
        "intermediate", "Intermediate", 1600, 300,
        "Punishes obvious blunders and holds a plan.",
    ),
    "advanced": Level(
        "advanced", "Advanced", 2000, 500,
        "Strong tactically; you'll need real accuracy to win.",
    ),
    "master": Level(
        "master", "Master", 2600, 800,
        "Near-full strength. Expect to be outplayed.",
    ),
}

DEFAULT_LEVEL = "intermediate"


def get_level(key: str | None) -> Level:
    return LEVELS.get((key or DEFAULT_LEVEL).lower(), LEVELS[DEFAULT_LEVEL])


def game_status(board: chess.Board) -> tuple[str, str | None]:
    """Return (status, result) for a board.

    status: "in_progress" | "checkmate" | "stalemate" | "draw"
    result: "1-0" | "0-1" | "1/2-1/2" | None
    """
    if board.is_checkmate():
        # The side to move is mated, so the other side won.
        return "checkmate", "0-1" if board.turn == chess.WHITE else "1-0"
    if board.is_stalemate():
        return "stalemate", "1/2-1/2"
    if board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return "draw", "1/2-1/2"
    return "in_progress", None


def build_pgn(moves_san: list[str], *, white: str, black: str, result: str | None) -> str:
    """Assemble a PGN so an AI game can be reviewed like any imported game."""
    header = (
        f'[Event "Vision64 AI game"]\n'
        f'[White "{white}"]\n'
        f'[Black "{black}"]\n'
        f'[Result "{result or "*"}"]\n\n'
    )
    body_parts: list[str] = []
    for i, san in enumerate(moves_san):
        if i % 2 == 0:
            body_parts.append(f"{i // 2 + 1}.")
        body_parts.append(san)
    body_parts.append(result or "*")
    return header + " ".join(body_parts)
