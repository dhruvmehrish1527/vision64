"""Schemas for the puzzle trainer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PuzzleSchema(BaseModel):
    """A puzzle served to the client — WITHOUT the solution (never leaked)."""

    id: int
    fen: str
    theme: str
    rating: int
    side_to_move: str  # "white" | "black"
    player_move_count: int  # how many moves the solver must find


class PuzzleMoveRequest(BaseModel):
    player_move_index: int = Field(ge=0, description="Which of the solver's moves this is (0-based).")
    uci: str
    time_ms: int | None = None


class PuzzleMoveResponse(BaseModel):
    correct: bool
    solved: bool
    opponent_reply_uci: str | None = None  # auto-played reply after a correct move
    solution_uci: list[str] | None = None  # revealed only when the attempt ends wrong
    new_puzzle_rating: int | None = None


class GenerateFromGameRequest(BaseModel):
    game_id: int


class GenerateResponse(BaseModel):
    created: int
