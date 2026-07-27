"""Health and readiness checks."""

from __future__ import annotations

import shutil

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness plus a quick report on whether dependencies are reachable."""
    settings = get_settings()
    stockfish_ok = shutil.which(settings.stockfish_path) is not None or "/" in settings.stockfish_path
    return {
        "status": "ok",
        "environment": settings.environment,
        "stockfish_configured": stockfish_ok,
        "coach_configured": bool(settings.anthropic_api_key),
    }
