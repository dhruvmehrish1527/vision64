"""Request/response schemas for analysis and coaching endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


# ---- Requests ----

class PositionRequest(BaseModel):
    fen: str = Field(default=START_FEN, description="Position to analyse (FEN).")
    multipv: int = Field(default=5, ge=1, le=8, description="How many candidate moves.")
    depth: int | None = Field(default=None, ge=1, le=30)
    rating: int = Field(default=1200, ge=100, le=3000, description="Player Elo, drives coaching.")
    explain: bool = Field(default=False, description="Also generate a coaching explanation.")


class ExplainMoveRequest(BaseModel):
    fen_before: str
    move_uci: str = Field(description="The played move in UCI, e.g. 'g1f3'.")
    rating: int = Field(default=1200, ge=100, le=3000)


class ExplainPositionRequest(BaseModel):
    fen: str = Field(default=START_FEN)
    rating: int = Field(default=1200, ge=100, le=3000)
    depth: int | None = Field(default=None, ge=1, le=30)


# ---- Responses ----

class CandidateSchema(BaseModel):
    move_uci: str
    move_san: str
    eval_cp: int | None
    mate_in: int | None
    pv: list[str]


class EngineSchema(BaseModel):
    fen: str
    depth: int
    eval_cp: int | None
    mate_in: int | None
    best_move: str | None
    best_move_san: str | None
    pv: list[str]
    candidates: list[CandidateSchema]


class ClassificationSchema(BaseModel):
    classification: str
    centipawn_loss: int
    tags: list[str]


class PositionResponse(BaseModel):
    engine: EngineSchema
    explanation: str | None = None


class ExplainMoveResponse(BaseModel):
    engine: EngineSchema
    classification: ClassificationSchema
    explanation: str
