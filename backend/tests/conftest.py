"""Pytest configuration: ensure the app package is importable and use a temp DB."""

from __future__ import annotations

import os

# Force an isolated SQLite database and dev-auth bypass for the test run before
# app modules read settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_vision64.db")
os.environ.setdefault("AUTH_DEV_BYPASS", "true")
os.environ.setdefault("ENVIRONMENT", "test")
