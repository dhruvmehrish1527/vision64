"""Deterministic move classification.

Turns two engine evaluations (the position before a move, and after it) into a
human label — Brilliant, Great, Excellent, Good, Book, Interesting, Inaccuracy,
Mistake, or Blunder — plus a set of tactical *tags* used by the weakness
tracker.

This is pure, testable arithmetic over engine output. No LLM. The AI coach later
*explains* the label this module assigns, so the two never disagree.

Convention: evaluations passed in are centipawns **from White's perspective**
(matching `EngineService`). We convert to the moving side's perspective
internally so "loss" is always ≥ 0 for a mistake, regardless of color.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import chess

# A mate is scored as this magnitude so it dominates any real centipawn value.
MATE_VALUE = 100_000

# Approximate material values (centipawns) for hanging-piece detection.
PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


class Classification(str, Enum):
    BRILLIANT = "Brilliant"
    GREAT = "Great"
    EXCELLENT = "Excellent"
    GOOD = "Good"
    BOOK = "Book"
    INTERESTING = "Interesting"
    INACCURACY = "Inaccuracy"
    MISTAKE = "Mistake"
    BLUNDER = "Blunder"


@dataclass
class ClassificationResult:
    classification: Classification
    centipawn_loss: int
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "classification": self.classification.value,
            "centipawn_loss": self.centipawn_loss,
            "tags": self.tags,
        }


def _mover_cp(eval_cp_white: int | None, mate_in: int | None, mover_is_white: bool) -> int:
    """Collapse (eval_cp, mate_in) into a single mover-relative centipawn score."""
    if mate_in is not None:
        # mate_in is signed from White's perspective in our convention.
        signed = MATE_VALUE - abs(mate_in) if mate_in > 0 else -(MATE_VALUE - abs(mate_in))
        value = signed
    else:
        value = eval_cp_white or 0
    return value if mover_is_white else -value


def _is_sacrifice(board_before: chess.Board, move: chess.Move) -> bool:
    """True if the move gives up material that isn't immediately recaptured.

    Heuristic used to distinguish a Brilliant/Interesting sacrifice from a
    routine capture: the moving side ends the move down material on that square
    (moves a piece into capture, or gives up more than it takes).
    """
    moving_piece = board_before.piece_at(move.from_square)
    if moving_piece is None:
        return False

    captured = board_before.piece_at(move.to_square)
    gained = PIECE_VALUE.get(captured.piece_type, 0) if captured else 0

    board_after = board_before.copy()
    board_after.push(move)

    # If the destination square is attacked by the opponent and not adequately
    # defended, the moving piece is hanging — a potential sacrifice.
    attackers = board_after.attackers(not moving_piece.color, move.to_square)
    if not attackers:
        return False
    risked = PIECE_VALUE.get(moving_piece.piece_type, 0)
    return risked > gained + 50  # gives up meaningfully more than it takes


def _hangs_piece(board_after: chess.Board, best_reply_uci: str | None) -> bool:
    """True if the opponent's best reply wins material by a capture."""
    if not best_reply_uci:
        return False
    try:
        reply = chess.Move.from_uci(best_reply_uci)
    except ValueError:
        return False
    victim = board_after.piece_at(reply.to_square)
    if victim is None:
        return False
    # A capture worth a minor piece or more that the opponent's best move grabs.
    return PIECE_VALUE.get(victim.piece_type, 0) >= 300


def classify_move(
    *,
    board_before: chess.Board,
    move: chess.Move,
    eval_before_white: int | None,
    mate_before: int | None,
    eval_after_white: int | None,
    mate_after: int | None,
    best_move_uci: str | None,
    best_reply_uci: str | None = None,
    ply: int = 1,
) -> ClassificationResult:
    """Classify a single move.

    Parameters mirror the engine read-outs before and after the move. `ply` lets
    us mark early theory as ``Book``.
    """
    mover_is_white = board_before.turn == chess.WHITE

    before = _mover_cp(eval_before_white, mate_before, mover_is_white)
    after = _mover_cp(eval_after_white, mate_after, mover_is_white)

    # Centipawn loss from the mover's perspective; clamp to non-negative.
    cpl = max(0, before - after)

    played_best = best_move_uci is not None and move.uci() == best_move_uci

    board_after = board_before.copy()
    board_after.push(move)

    tags: list[str] = []

    # ---- Tactical tags (fuel the weakness tracker) ----
    if mate_before is not None and mate_after is None and before > 0:
        tags.append("missed_mate")
    if before > 300 and after < 100:
        tags.append("missed_win")
    if _hangs_piece(board_after, best_reply_uci):
        tags.append("hanging_piece")
    if before >= -50 and after <= -300:
        tags.append("blundered_material")

    sacrifice = _is_sacrifice(board_before, move)

    # ---- Classification decision tree ----
    # Book: early game, played the engine's top move, roughly balanced.
    if ply <= 10 and played_best and abs(after) < 80:
        return ClassificationResult(Classification.BOOK, cpl, tags)

    # Brilliant: a sound sacrifice that stays best (or near-best) and winning-ish.
    if sacrifice and cpl <= 30 and after >= -50:
        tags.append("sacrifice")
        return ClassificationResult(Classification.BRILLIANT, cpl, tags)

    # Great: found the only good move in a sharp spot (played best, small loss,
    # but the position was critical — a big swing was available to go wrong).
    if played_best and cpl == 0 and abs(before) > 150:
        return ClassificationResult(Classification.GREAT, cpl, tags)

    if cpl <= 10:
        return ClassificationResult(Classification.EXCELLENT, cpl, tags)
    if cpl <= 40:
        return ClassificationResult(Classification.GOOD, cpl, tags)
    if cpl <= 90:
        # A defensible non-best try rather than a clear error.
        return ClassificationResult(Classification.INTERESTING, cpl, tags)
    if cpl <= 150:
        return ClassificationResult(Classification.INACCURACY, cpl, tags)
    if cpl <= 300:
        return ClassificationResult(Classification.MISTAKE, cpl, tags)
    return ClassificationResult(Classification.BLUNDER, cpl, tags)
