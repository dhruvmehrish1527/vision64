"""Schemas for the AI opponent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LevelSchema(BaseModel):
    key: str
    label: str
    elo: int
    blurb: str


class NewGameRequest(BaseModel):
    level: str = Field(default="intermediate")
    play_as: str = Field(default="white", description='"white" | "black"')


class AiGameState(BaseModel):
    game_id: int
    fen: str
    status: str                      # in_progress | checkmate | stalemate | draw
    result: str | None = None
    player_color: str
    level: str
    moves_san: list[str] = []
    last_move_uci: str | None = None  # the AI's reply, for board animation
    your_turn: bool = True


class PlayMoveRequest(BaseModel):
    uci: str = Field(description="The player's move in UCI, e.g. 'e2e4'.")


class GameFeedback(BaseModel):
    accuracy: float
    summary: str
    biggest_mistake_ply: int | None = None
    weakness_tags: dict = {}
