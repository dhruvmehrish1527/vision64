"""Aggregate router: mounts every domain router under /api."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai_game,
    analysis,
    games,
    health,
    openings,
    puzzles,
    social,
    training,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analysis.router)
api_router.include_router(ai_game.router)
api_router.include_router(games.router)
api_router.include_router(users.router)
api_router.include_router(puzzles.router)
api_router.include_router(training.router)
api_router.include_router(openings.router)
api_router.include_router(social.router)
