"""Clerk JWT verification and the `get_current_user` dependency.

Flow: the frontend obtains a Clerk session JWT and sends it as
`Authorization: Bearer <jwt>`. We verify the signature against Clerk's JWKS
(cached), check the issuer, extract the Clerk user id (`sub`), and upsert a
local `User` row so all chess data is user-scoped.

`AUTH_DEV_BYPASS=true` short-circuits to a stable dev user so the app runs
end-to-end locally without a Clerk project configured.
"""

from __future__ import annotations

import functools
import time

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User

logger = get_logger(__name__)
settings = get_settings()

DEV_CLERK_ID = "dev_user"


@functools.lru_cache
def _jwk_client() -> PyJWKClient:
    if not settings.clerk_jwks_url:
        raise RuntimeError("CLERK_JWKS_URL is not configured.")
    return PyJWKClient(settings.clerk_jwks_url)


def _verify_token(token: str) -> dict:
    """Verify a Clerk JWT and return its claims, or raise 401."""
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},  # Clerk session tokens omit `aud`
        )
        return claims
    except Exception as exc:
        logger.info("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc


def _upsert_user(db: Session, *, clerk_id: str, email: str | None, name: str | None) -> User:
    user = db.query(User).filter(User.clerk_id == clerk_id).one_or_none()
    if user is None:
        user = User(clerk_id=clerk_id, email=email, display_name=name)
        db.add(user)
    else:
        if email and user.email != email:
            user.email = email
        if name and user.display_name != name:
            user.display_name = name
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """FastAPI dependency: resolve the authenticated (or dev) user."""
    if settings.auth_dev_bypass:
        return _upsert_user(
            db, clerk_id=DEV_CLERK_ID, email="dev@vision64.local", name="Dev Player"
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    token = authorization.split(" ", 1)[1].strip()
    claims = _verify_token(token)
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no subject.",
        )

    return _upsert_user(
        db,
        clerk_id=clerk_id,
        email=claims.get("email"),
        name=claims.get("name") or claims.get("username"),
    )
