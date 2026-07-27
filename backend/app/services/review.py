"""Whole-game review orchestration.

Walks a parsed game move by move, evaluating each position with the engine,
classifying every move, and aggregating the result into:

* per-side accuracy scores,
* the biggest mistake,
* turning points (large evaluation swings),
* a phase-by-phase (opening / middlegame / endgame) breakdown,
* a tally of weakness tags for the weakness tracker.

Accuracy uses a win-probability model (à la Lichess): evaluations are mapped to
a win percentage, and each move's accuracy reflects how much win probability it
preserved. This is more faithful than raw centipawn loss because a 100cp slip
matters far more near equality than in a already-won position.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

import chess

from app.core.logging import get_logger
from app.services.chess_io import ParsedGame, ParsedMove
from app.services.classifier import Classification, classify_move
from app.services.engine import EngineService

logger = get_logger(__name__)


def _win_percent(eval_cp: int | None, mate_in: int | None) -> float:
    """Map a White-perspective evaluation to White's win probability (0–100)."""
    if mate_in is not None:
        return 100.0 if mate_in > 0 else 0.0
    cp = eval_cp or 0
    # Logistic curve tuned so ~+300cp ≈ 75% and ~+700cp ≈ 90%.
    return 50 + 50 * (2 / (1 + math.exp(-0.004 * cp)) - 1)


def _move_accuracy(win_before: float, win_after: float) -> float:
    """Accuracy (0–100) for one move given win% before/after from mover's view."""
    drop = max(0.0, win_before - win_after)
    acc = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, acc))


@dataclass
class ReviewedMove:
    ply: int
    color: str
    san: str
    uci: str
    fen_before: str
    eval_cp: int | None
    mate_in: int | None
    best_move: str | None
    best_pv: list[str]  # engine's best line from the position BEFORE this move
    classification: str
    centipawn_loss: int
    tags: list[str] = field(default_factory=list)


@dataclass
class GameReviewResult:
    accuracy_white: float
    accuracy_black: float
    biggest_mistake_ply: int | None
    turning_points: list[int]
    phases: dict
    weakness_tags: dict
    moves: list[ReviewedMove]


class ReviewService:
    def __init__(self, engine: EngineService, depth: int = 14) -> None:
        # A shallower depth keeps full-game review affordable; the analysis board
        # uses deeper searches for single positions.
        self.engine = engine
        self.depth = depth

    def review(self, game: ParsedGame) -> GameReviewResult:
        reviewed: list[ReviewedMove] = []
        white_accs: list[float] = []
        black_accs: list[float] = []
        tag_counter: Counter[str] = Counter()
        turning_points: list[int] = []

        prev_eval_white: int | None = 0
        prev_mate: int | None = None
        prev_win = _win_percent(0, None)

        for pm in game.moves:
            before = self.engine.analyse(pm.fen_before, multipv=1, depth=self.depth)
            after = self.engine.analyse(pm.fen_after, multipv=1, depth=self.depth)

            board_before = chess.Board(pm.fen_before)
            move = chess.Move.from_uci(pm.uci)

            result = classify_move(
                board_before=board_before,
                move=move,
                eval_before_white=before.eval_cp,
                mate_before=before.mate_in,
                eval_after_white=after.eval_cp,
                mate_after=after.mate_in,
                best_move_uci=before.best_move,
                best_reply_uci=after.best_move,
                ply=pm.ply,
            )

            # Accuracy from the mover's win-probability change.
            win_before = _win_percent(before.eval_cp, before.mate_in)
            win_after = _win_percent(after.eval_cp, after.mate_in)
            if pm.color == "white":
                acc = _move_accuracy(win_before, win_after)
                white_accs.append(acc)
            else:
                # Flip perspective for Black.
                acc = _move_accuracy(100 - win_before, 100 - win_after)
                black_accs.append(acc)

            # Turning point: a swing of ≥ 25 win-percentage points.
            if abs(win_after - prev_win) >= 25:
                turning_points.append(pm.ply)

            for tag in result.tags:
                tag_counter[tag] += 1

            reviewed.append(
                ReviewedMove(
                    ply=pm.ply,
                    color=pm.color,
                    san=pm.san,
                    uci=pm.uci,
                    fen_before=pm.fen_before,
                    eval_cp=after.eval_cp,
                    mate_in=after.mate_in,
                    best_move=before.best_move,
                    best_pv=before.pv,
                    classification=result.classification.value,
                    centipawn_loss=result.centipawn_loss,
                    tags=result.tags,
                )
            )
            prev_win = win_after

        biggest = self._biggest_mistake(reviewed)
        phases = self._phase_breakdown(reviewed)

        return GameReviewResult(
            accuracy_white=round(sum(white_accs) / len(white_accs), 1) if white_accs else 0.0,
            accuracy_black=round(sum(black_accs) / len(black_accs), 1) if black_accs else 0.0,
            biggest_mistake_ply=biggest,
            turning_points=turning_points,
            phases=phases,
            weakness_tags=dict(tag_counter),
            moves=reviewed,
        )

    @staticmethod
    def _biggest_mistake(moves: list[ReviewedMove]) -> int | None:
        worst: ReviewedMove | None = None
        for m in moves:
            if worst is None or m.centipawn_loss > worst.centipawn_loss:
                worst = m
        return worst.ply if worst and worst.centipawn_loss > 90 else None

    @staticmethod
    def _phase_breakdown(moves: list[ReviewedMove]) -> dict:
        """Split moves into opening (≤ply 20), middlegame, endgame (last third)."""
        if not moves:
            return {}
        total = len(moves)
        opening_cut = min(20, total)
        endgame_start = max(opening_cut, total - total // 3)

        def summarise(chunk: list[ReviewedMove]) -> dict:
            counts = Counter(m.classification for m in chunk)
            avg_loss = (
                round(sum(m.centipawn_loss for m in chunk) / len(chunk), 1)
                if chunk else 0.0
            )
            return {"move_count": len(chunk), "avg_cp_loss": avg_loss, "labels": dict(counts)}

        return {
            "opening": summarise(moves[:opening_cut]),
            "middlegame": summarise(moves[opening_cut:endgame_start]),
            "endgame": summarise(moves[endgame_start:]),
        }
