"""Vision64 FastAPI application entrypoint.

Wires together configuration, logging, CORS, and the API router. Import this as
`app.main:app` (uvicorn / gunicorn).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Vision64 API",
    version="0.1.0",
    description="AI-powered chess coaching — engine analysis with human explanations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "Vision64 API starting (env=%s, coach=%s, dev_auth_bypass=%s)",
        settings.environment,
        "configured" if settings.anthropic_api_key else "missing",
        settings.auth_dev_bypass,
    )
    # Seed curated puzzles once (no-op if already seeded or engine missing).
    from app.db.session import SessionLocal
    from app.services.seed import seed_puzzles

    db = SessionLocal()
    try:
        seed_puzzles(db)
    except Exception as exc:  # never block startup on seeding
        logger.warning("Puzzle seeding skipped: %s", exc)
    finally:
        db.close()


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Terminate pooled Stockfish processes so none are orphaned."""
    from app.services.engine import engine_service

    engine_service.pool.shutdown()
    logger.info("Engine pool shut down.")


@app.get("/")
def root() -> dict:
    return {"name": "Vision64 API", "docs": "/docs", "health": "/api/health"}
