"""The AI coach.

Turns engine facts + a deterministic classification into a beginner-friendly,
rating-adaptive explanation, using the Claude API.

The prompt is *grounded*: the engine's evaluation, best line, and the
classification are passed as facts, and Claude is asked to **explain** them for a
player of a given strength — not to re-evaluate the position. This keeps the
coaching accurate (the numbers come from Stockfish) while the language stays
warm and instructive.

Model: `claude-opus-5` with adaptive thinking. The stable coaching rubric is
sent as a cached system prompt so repeated calls are inexpensive.
"""

from __future__ import annotations

import chess

from app.core.config import get_settings
from app.core.logging import get_logger, timed

logger = get_logger(__name__)


class CoachUnavailable(RuntimeError):
    """Raised when the coach cannot produce an explanation (no API key, etc.)."""


# The rating bands the coach adapts to. Each carries a short teaching stance.
RATING_BANDS = [
    (0, 1000, "a beginner (600–1000). Explain core ideas simply, avoid jargon, "
              "and name the single most important takeaway."),
    (1000, 1400, "an improving club player (1000–1400). You can use basic terms "
                 "like 'development', 'outpost', and 'pin', but keep it concrete."),
    (1400, 1800, "an intermediate player (1400–1800). Use standard chess "
                 "vocabulary and discuss plans a few moves deep."),
    (1800, 3000, "an advanced player (1800–2200). Be precise and concise; assume "
                 "strong fundamentals and focus on nuance and long-term plans."),
]

SYSTEM_PROMPT = """\
You are Vision64's chess coach. You explain WHY moves are good or bad so players \
improve — you never just state the best move.

You are always given trustworthy facts from the Stockfish engine and a \
deterministic move classification. Treat these as ground truth: your job is to \
EXPLAIN them, not to re-evaluate the position or invent different numbers.

Every explanation should, where relevant to the position, weave together:
- Tactical ideas (threats, captures, forks, pins, checks)
- Strategic ideas (space, structure, piece activity, weak squares)
- King safety
- Pawn structure
- Long-term plans
- The typical mistake a player at this level makes here

Rules:
- Be encouraging and clear. Lead with the single most useful idea.
- Ground every claim in the engine facts provided; do not contradict the eval.
- Keep it to 2–5 tight sentences unless the position is genuinely complex.
- Never output raw centipawn numbers to a beginner; translate them ("you're \
clearly better", "roughly equal", "you're losing material").
- Do not use markdown headers or bullet lists; write natural prose.\
"""


def _band_stance(rating: int) -> str:
    for lo, hi, stance in RATING_BANDS:
        if lo <= rating < hi:
            return stance
    return RATING_BANDS[-1][2]


def _eval_phrase(eval_cp: int | None, mate_in: int | None) -> str:
    """Human phrase for the eval, so the coach reasons over words, not just numbers."""
    if mate_in is not None:
        side = "White" if mate_in > 0 else "Black"
        return f"forced mate for {side} in {abs(mate_in)}"
    if eval_cp is None:
        return "unclear"
    pawns = eval_cp / 100
    if abs(pawns) < 0.3:
        return f"roughly equal ({pawns:+.1f})"
    leader = "White" if pawns > 0 else "Black"
    magnitude = "slightly" if abs(pawns) < 1 else "clearly" if abs(pawns) < 3 else "winning —"
    return f"{leader} is {magnitude} better ({pawns:+.1f})"


class CoachService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None  # lazy — avoid importing/instantiating when unused

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        if not self.settings.anthropic_api_key:
            raise CoachUnavailable(
                "ANTHROPIC_API_KEY is not set; the AI coach is unavailable."
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise CoachUnavailable("The `anthropic` package is not installed.") from exc
        self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    # ---- Prompt builders (shared by sync + streaming) ----

    @staticmethod
    def _move_prompt(
        *,
        fen_before: str,
        played_san: str,
        rating: int,
        eval_cp: int | None,
        mate_in: int | None,
        best_move_san: str | None,
        classification: str,
        tags: list[str],
        pv_san: list[str] | None,
    ) -> str:
        try:
            side = "White" if chess.Board(fen_before).turn == chess.WHITE else "Black"
        except ValueError:
            side = "the side to move"

        facts = [
            f"Player strength: {_band_stance(rating)}",
            f"Side to move: {side}",
            f"Move played: {played_san}",
            f"Engine's best move: {best_move_san or 'unknown'}",
            f"Classification (trust this): {classification}",
            f"Evaluation after the move: {_eval_phrase(eval_cp, mate_in)}",
        ]
        if pv_san:
            facts.append(f"Engine's main line: {' '.join(pv_san[:6])}")
        if tags:
            facts.append(f"Detected patterns: {', '.join(t.replace('_', ' ') for t in tags)}")

        return (
            "Explain this move to the player.\n\n"
            + "\n".join(f"- {f}" for f in facts)
            + f"\n\nPosition (FEN): {fen_before}\n\nWrite the explanation now."
        )

    @staticmethod
    def _position_prompt(*, fen: str, rating: int, engine: dict) -> str:
        eval_phrase = _eval_phrase(engine.get("eval_cp"), engine.get("mate_in"))
        best = engine.get("best_move_san") or "unknown"
        return (
            "Explain this position and the plan for the side to move.\n\n"
            f"- Player strength: {_band_stance(rating)}\n"
            f"- Evaluation: {eval_phrase}\n"
            f"- Engine's suggested move: {best}\n"
            f"- Position (FEN): {fen}\n\n"
            "Cover the key ideas and the concrete plan. Write it now."
        )

    # ---- Synchronous ----

    def explain_move(self, **kwargs) -> str:
        """Explain a single played move for a player of the given rating."""
        return self._complete(self._move_prompt(**kwargs), max_tokens=600)

    def explain_position(self, *, fen: str, rating: int, engine: dict) -> str:
        """Explain what's going on in a position and what the plan should be."""
        return self._complete(
            self._position_prompt(fen=fen, rating=rating, engine=engine), max_tokens=700
        )

    # ---- Streaming (token-by-token, for a responsive UI) ----

    def stream_move(self, **kwargs):
        yield from self._stream(self._move_prompt(**kwargs), max_tokens=600)

    def stream_position(self, *, fen: str, rating: int, engine: dict):
        yield from self._stream(
            self._position_prompt(fen=fen, rating=rating, engine=engine), max_tokens=700
        )

    def _stream(self, user_content: str, *, max_tokens: int):
        """Yield explanation text chunks as Claude generates them."""
        client = self._client_or_raise()
        try:
            with timed(logger, "coach.stream"):
                with client.messages.stream(
                    model=self.settings.coach_model,
                    max_tokens=max_tokens,
                    thinking={"type": "adaptive"},
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_content}],
                ) as stream:
                    for text in stream.text_stream:
                        if text:
                            yield text
        except Exception as exc:
            logger.warning("coach stream failed: %s", exc)
            raise CoachUnavailable(str(exc)) from exc

    def _complete(self, user_content: str, *, max_tokens: int) -> str:
        client = self._client_or_raise()
        try:
            with timed(logger, "coach.complete"):
                response = client.messages.create(
                    model=self.settings.coach_model,
                    max_tokens=max_tokens,
                    thinking={"type": "adaptive"},
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            # Cache the rubric so repeated coaching calls are cheap.
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_content}],
                )
        except Exception as exc:  # anthropic errors, network, etc.
            logger.warning("coach call failed: %s", exc)
            raise CoachUnavailable(str(exc)) from exc

        # `stop_reason` may be "refusal" on rare safety declines — handle it.
        if getattr(response, "stop_reason", None) == "refusal":
            raise CoachUnavailable("The coach could not respond to this request.")

        parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        if not text:
            raise CoachUnavailable("The coach returned an empty explanation.")
        return text


coach_service = CoachService()
