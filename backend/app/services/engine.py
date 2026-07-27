"""Stockfish engine service.

Drives the Stockfish binary over the UCI protocol via `python-chess`. Exposes a
single high-level `analyse()` that returns everything the product needs from the
engine: the evaluation bar value, the best move, the top-N candidate moves, the
principal variation, search depth, and mate detection.

Design notes
------------
* We open a fresh engine per analysis call and close it deterministically. A
  long-lived pool is a Phase-4 optimization; correctness and isolation come
  first (a wedged engine can't poison later requests).
* All evaluations are normalized to **centipawns from White's perspective**, so
  the eval bar and classifier share one convention. Mates are reported
  separately in `mate_in`.
* If the binary is missing we raise `EngineUnavailable`, which the API layer
  turns into a clean 503 with an actionable message rather than a stack trace.
"""

from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import chess
import chess.engine

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# A mate is represented internally as a very large centipawn value so it always
# sorts correctly against real evaluations. The sign carries which side mates.
MATE_SCORE = 100_000


class EngineUnavailable(RuntimeError):
    """Raised when the Stockfish binary cannot be launched."""


@dataclass
class Candidate:
    """One candidate move from a multi-PV search."""

    move_uci: str
    move_san: str
    eval_cp: int | None            # White's perspective; None if this line is a mate
    mate_in: int | None            # signed; +N mate for side to move, -N mate against
    pv: list[str] = field(default_factory=list)  # principal variation as UCI strings

    def to_dict(self) -> dict:
        return {
            "move_uci": self.move_uci,
            "move_san": self.move_san,
            "eval_cp": self.eval_cp,
            "mate_in": self.mate_in,
            "pv": self.pv,
        }


@dataclass
class EngineResult:
    """The full engine read-out for a position."""

    fen: str
    depth: int
    eval_cp: int | None            # White's perspective
    mate_in: int | None
    best_move: str | None          # UCI
    best_move_san: str | None
    pv: list[str]                  # principal variation of the best line (UCI)
    candidates: list[Candidate]

    def to_dict(self) -> dict:
        return {
            "fen": self.fen,
            "depth": self.depth,
            "eval_cp": self.eval_cp,
            "mate_in": self.mate_in,
            "best_move": self.best_move,
            "best_move_san": self.best_move_san,
            "pv": self.pv,
            "candidates": [c.to_dict() for c in self.candidates],
        }


class EnginePool:
    """A pool of warm, reusable Stockfish processes.

    Opening a process and completing the UCI handshake costs ~50–150 ms; a
    full-game review does dozens of analyses, so spawning per call dominated
    latency. The pool keeps a small set of engines alive and hands one out per
    call. `SimpleEngine` is single-threaded, so each engine is used by exactly
    one caller at a time — `acquire()` blocks until one is free, which also caps
    concurrent CPU use. FastAPI runs sync endpoints in a threadpool, so parallel
    requests each borrow a distinct engine safely.
    """

    def __init__(self, size: int) -> None:
        self.settings = get_settings()
        self.size = max(1, size)
        self._pool: "queue.Queue[chess.engine.SimpleEngine]" = queue.Queue()
        self._lock = threading.Lock()
        self._started = False

    def _create(self) -> chess.engine.SimpleEngine:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.settings.stockfish_path)
        except FileNotFoundError as exc:
            raise EngineUnavailable(
                f"Stockfish binary not found at '{self.settings.stockfish_path}'. "
                "Install it (e.g. `brew install stockfish`) or set STOCKFISH_PATH."
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise EngineUnavailable(f"Could not start Stockfish: {exc}") from exc
        engine.configure(
            {"Threads": self.settings.engine_threads, "Hash": self.settings.engine_hash_mb}
        )
        return engine

    def _ensure_started(self) -> None:
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            for _ in range(self.size):
                self._pool.put(self._create())
            self._started = True
            logger.info("Engine pool started with %d Stockfish process(es).", self.size)

    @contextmanager
    def acquire(self) -> "Iterator[chess.engine.SimpleEngine]":
        """Borrow an engine; a crashed engine is transparently replaced."""
        self._ensure_started()
        engine = self._pool.get()
        healthy = True
        try:
            yield engine
        except chess.engine.EngineError:
            # The engine misbehaved on this position — recycle the process.
            healthy = False
            raise
        finally:
            if healthy:
                self._pool.put(engine)
            else:
                try:
                    engine.quit()
                except Exception:  # pragma: no cover
                    pass
                self._pool.put(self._create())

    def shutdown(self) -> None:
        while not self._pool.empty():
            try:
                self._pool.get_nowait().quit()
            except Exception:  # pragma: no cover
                pass


class EngineService:
    """Thin, safe wrapper around the Stockfish pool."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.pool = EnginePool(self.settings.engine_pool_size)

    @staticmethod
    def _score_to_cp(score: chess.engine.PovScore) -> tuple[int | None, int | None]:
        """Return (eval_cp_white, mate_in) from a POV score.

        `mate_in` is signed from the side-to-move perspective (python-chess
        convention preserved). `eval_cp` is White-relative and is None on mate.
        """
        white = score.white()
        if white.is_mate():
            mate = white.mate()  # +N: white mates in N; -N: black mates in N
            return None, mate
        return white.score(), None

    def analyse(
        self,
        fen: str,
        *,
        multipv: int | None = None,
        depth: int | None = None,
    ) -> EngineResult:
        """Analyse a FEN and return the best move, candidates, eval, and PV.

        Raises `EngineUnavailable` if Stockfish can't run, and `ValueError` if
        the FEN is illegal.
        """
        try:
            board = chess.Board(fen)
        except ValueError as exc:
            raise ValueError(f"Illegal FEN: {fen}") from exc

        multipv = multipv or self.settings.engine_multipv
        depth = depth or self.settings.engine_default_depth
        limit = chess.engine.Limit(depth=depth)

        with self.pool.acquire() as engine:
            infos = engine.analyse(board, limit, multipv=multipv)

        # `analyse` with multipv returns a list; without it, a single dict.
        if isinstance(infos, dict):
            infos = [infos]

        candidates: list[Candidate] = []
        for info in infos:
            pv_moves = info.get("pv", [])
            if not pv_moves:
                continue
            first = pv_moves[0]
            eval_cp, mate_in = self._score_to_cp(info["score"])
            candidates.append(
                Candidate(
                    move_uci=first.uci(),
                    move_san=board.san(first),
                    eval_cp=eval_cp,
                    mate_in=mate_in,
                    pv=[m.uci() for m in pv_moves],
                )
            )

        best = candidates[0] if candidates else None
        return EngineResult(
            fen=fen,
            depth=depth,
            eval_cp=best.eval_cp if best else None,
            mate_in=best.mate_in if best else None,
            best_move=best.move_uci if best else None,
            best_move_san=best.move_san if best else None,
            pv=best.pv if best else [],
            candidates=candidates,
        )

    def evaluate_only(self, fen: str, *, depth: int | None = None) -> tuple[int | None, int | None]:
        """Fast single-line evaluation — used by the classifier per move.

        Returns (eval_cp_white, mate_in).
        """
        result = self.analyse(fen, multipv=1, depth=depth)
        return result.eval_cp, result.mate_in

    def play_move(
        self,
        fen: str,
        *,
        elo: int,
        limit_strength: bool = True,
        movetime_ms: int = 300,
        depth: int | None = None,
    ) -> str | None:
        """Pick a move at a target playing strength — the AI opponent.

        Uses Stockfish's own `UCI_LimitStrength`/`UCI_Elo`, which weakens the
        engine by making *human-like* errors rather than by simply searching
        shallower, so lower levels feel like a real opponent instead of a
        random-move bot. Returns UCI, or None if the game is already over.

        The pooled engine's strength options are set for this call and reset
        afterwards, so a weakened opponent never leaks into analysis calls that
        share the same process.
        """
        try:
            board = chess.Board(fen)
        except ValueError as exc:
            raise ValueError(f"Illegal FEN: {fen}") from exc
        if board.is_game_over():
            return None

        # Stockfish accepts roughly 1320–3190 for UCI_Elo; clamp into range.
        target = max(1320, min(3190, elo))
        limit = (
            chess.engine.Limit(depth=depth)
            if depth is not None
            else chess.engine.Limit(time=movetime_ms / 1000)
        )

        with self.pool.acquire() as engine:
            try:
                if limit_strength:
                    engine.configure({"UCI_LimitStrength": True, "UCI_Elo": target})
                result = engine.play(board, limit)
            finally:
                # Always restore full strength for subsequent borrowers.
                if limit_strength:
                    engine.configure({"UCI_LimitStrength": False})

        return result.move.uci() if result.move else None


# Module-level singleton is fine: the service holds no mutable per-call state.
engine_service = EngineService()
