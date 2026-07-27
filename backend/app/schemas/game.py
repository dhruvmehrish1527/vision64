"""Schemas for game import and review."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportPgnRequest(BaseModel):
    pgn: str = Field(description="Full PGN text of one game.")
    review: bool = Field(default=True, description="Run a full engine review after import.")
    depth: int = Field(default=14, ge=6, le=22)


class ReviewedMoveSchema(BaseModel):
    ply: int
    color: str
    san: str
    uci: str
    fen_before: str | None = None
    eval_cp: int | None
    mate_in: int | None
    best_move: str | None
    best_pv: list[str] = []
    classification: str
    centipawn_loss: int
    tags: list[str]


class GameSummarySchema(BaseModel):
    id: int
    white: str | None
    black: str | None
    result: str | None
    source: str
    accuracy_white: float | None
    accuracy_black: float | None

    class Config:
        from_attributes = True


class GameReviewResponse(BaseModel):
    game: GameSummarySchema
    accuracy_white: float
    accuracy_black: float
    biggest_mistake_ply: int | None
    turning_points: list[int]
    phases: dict
    weakness_tags: dict
    moves: list[ReviewedMoveSchema]


class UserSchema(BaseModel):
    id: int
    display_name: str | None
    email: str | None
    rating: int
    puzzle_rating: int
    streak_days: int

    class Config:
        from_attributes = True
