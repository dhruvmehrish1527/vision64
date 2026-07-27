"""Puzzle generation and theming.

Two sources of puzzles:

1. **From a FEN, via the engine** (`build_from_fen`). A position becomes a puzzle
   only if it contains a *genuine tactic* — the best move is decisively better
   than the second-best (an "only move"), or it forces mate. The solution is the
   engine's principal variation, so it is always correct. Used for the curated
   seed set and one-off generation from any position.

2. **From a user's own blunders** (`generate_from_analyses`). Every Mistake/
   Blunder the review found is a position where the player *had* a strong move
   and missed it — the ideal "you missed this" training puzzle. The solution is
   the best line stored during review. This is what makes puzzles personal: you
   drill the exact tactics you keep missing.

Themes are inferred from the solution (mate length, whether the key move forks
or wins material) so the puzzle picker can target a user's weaknesses.
"""

from __future__ import annotations

import chess

from app.services.classifier import PIECE_VALUE
from app.services.engine import EngineService

# Themes the picker and weakness tracker share.
THEMES = [
    "mate_in_1", "mate_in_2", "mate_in_3", "mate_in_4", "mate_in_5",
    "fork", "pin", "skewer", "win_material", "endgame", "tactic",
]

# Map a classifier weakness tag to the puzzle theme that trains it.
TAG_TO_THEME = {
    "missed_mate": "mate_in_2",
    "missed_fork": "fork",
    "hanging_piece": "win_material",
    "blundered_material": "win_material",
    "missed_win": "tactic",
}


def _forks(fen: str, first_uci: str) -> bool:
    """True if the first solution move attacks two+ valuable enemy targets."""
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(first_uci)
    except ValueError:
        return False
    if move not in board.legal_moves:
        return False
    mover = board.turn
    board.push(move)
    # Count enemy pieces (queen/rook/minor, or the king) the moved piece attacks.
    targets = 0
    for sq in board.attacks(move.to_square):
        piece = board.piece_at(sq)
        if piece and piece.color != mover:
            if piece.piece_type == chess.KING or PIECE_VALUE.get(piece.piece_type, 0) >= 300:
                targets += 1
    return targets >= 2


def infer_theme(fen: str, solution_uci: list[str], mate_in: int | None) -> str:
    if mate_in is not None and mate_in > 0:
        return f"mate_in_{min(mate_in, 5)}"
    if solution_uci and _forks(fen, solution_uci[0]):
        return "fork"
    # Endgame heuristic: few pieces left.
    if len(chess.Board(fen).piece_map()) <= 8:
        return "endgame"
    return "win_material"


def build_from_fen(
    engine: EngineService,
    fen: str,
    *,
    rating: int = 1200,
    min_gap_cp: int = 200,
    line_plies: int = 4,
    depth: int = 16,
    theme_hint: str | None = None,
) -> dict | None:
    """Build a puzzle from a position, or return None if it isn't tactical.

    A position qualifies when the best move forces mate, or beats the
    second-best move by at least `min_gap_cp` centipawns (from the mover's
    perspective) — i.e. there is a clear, findable tactic.
    """
    try:
        board = chess.Board(fen)
    except ValueError:
        return None
    if board.is_game_over():
        return None

    result = engine.analyse(fen, multipv=2, depth=depth)
    if not result.candidates:
        return None
    best = result.candidates[0]

    is_mate = best.mate_in is not None and best.mate_in > 0
    qualifies = is_mate
    if not qualifies and len(result.candidates) >= 2:
        second = result.candidates[1]
        if best.eval_cp is not None and second.eval_cp is not None:
            sign = 1 if board.turn == chess.WHITE else -1
            gap = sign * best.eval_cp - sign * second.eval_cp
            qualifies = gap >= min_gap_cp
    if not qualifies:
        return None

    solution = best.pv[:line_plies] if best.pv else [best.move_uci]
    theme = theme_hint or infer_theme(fen, solution, best.mate_in)
    return {"fen": fen, "solution_uci": solution, "theme": theme, "rating": rating}


def generate_from_analyses(moves_with_analysis: list[dict], *, max_puzzles: int = 6) -> list[dict]:
    """Turn a reviewed game's blunders into personalized puzzles.

    `moves_with_analysis` items: {fen_before, classification, centipawn_loss,
    best_pv (list[str]), tags (list[str]), rating}.
    """
    puzzles: list[dict] = []
    for m in moves_with_analysis:
        if len(puzzles) >= max_puzzles:
            break
        if m.get("classification") not in {"Mistake", "Blunder"}:
            continue
        if (m.get("centipawn_loss") or 0) < 200:
            continue
        pv = m.get("best_pv") or []
        if not pv:
            continue

        fen = m["fen_before"]
        tags = m.get("tags") or []
        theme = next((TAG_TO_THEME[t] for t in tags if t in TAG_TO_THEME), None)
        theme = theme or infer_theme(fen, pv, None)
        puzzles.append(
            {
                "fen": fen,
                "solution_uci": pv[:4],
                "theme": theme,
                "rating": m.get("rating", 1200),
                "source": "from_game",
            }
        )
    return puzzles


# Curated seed positions — each is a known tactic. The engine computes the exact
# solution at seed time (see services/seed.py), so these only need a themed
# starting FEN where a decisive tactic exists for the side to move.
CURATED_FENS = [
    # Back-rank mate in one.
    ("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1", "mate_in_1"),
    # Knight fork of king and rook (Nf6+ then wins the exchange).
    ("4r1k1/5p1p/8/3N4/8/8/5PPP/6K1 w - - 0 1", "fork"),
    # Winning a hanging queen with a discovered/where best beats the rest.
    ("r1bqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 3", "mate_in_1"),
    # Simple king-and-pawn promotion tactic (endgame).
    ("8/P5k1/8/8/8/8/6K1/8 w - - 0 1", "endgame"),
]
