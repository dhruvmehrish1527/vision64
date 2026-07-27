"""Social features: shareable game links, follows, and bookmarks.

Sharing is **opt-in and revocable**: a game is private until its owner mints a
share token, and clearing the token immediately breaks every existing link. The
public view is deliberately read-only and exposes only the game itself — never
the owner's email, rating, or other games.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.follow import Follow
from app.models.game import Game
from app.models.social import Bookmark
from app.models.user import User

router = APIRouter(prefix="/social", tags=["social"])


# ---------- Schemas ----------

class ShareResponse(BaseModel):
    share_token: str
    url_path: str  # frontend route the owner can copy


class SharedGame(BaseModel):
    white: str | None
    black: str | None
    result: str | None
    pgn: str | None
    accuracy_white: float | None
    accuracy_black: float | None
    shared_by: str | None
    moves_san: list[str] = []


class BookmarkRequest(BaseModel):
    entity_type: str = Field(description='"game" | "puzzle" | "opening" | "lesson"')
    entity_id: int
    note: str | None = None


class BookmarkItem(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    note: str | None

    class Config:
        from_attributes = True


class PublicProfile(BaseModel):
    id: int
    display_name: str | None
    rating: int
    puzzle_rating: int
    games_analyzed: int
    followers: int
    following: int
    is_following: bool = False


# ---------- Sharing ----------

@router.post("/games/{game_id}/share", response_model=ShareResponse)
def share_game(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShareResponse:
    """Mint (or return) a public share link for one of your games."""
    game = (
        db.query(Game).filter(Game.id == game_id, Game.user_id == user.id).one_or_none()
    )
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found.")

    if not game.share_token:
        game.share_token = secrets.token_urlsafe(16)[:32]
        db.commit()
        db.refresh(game)

    return ShareResponse(share_token=game.share_token, url_path=f"/shared/{game.share_token}")


@router.delete("/games/{game_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def unshare_game(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Revoke sharing — every existing link stops working immediately."""
    game = (
        db.query(Game).filter(Game.id == game_id, Game.user_id == user.id).one_or_none()
    )
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found.")
    game.share_token = None
    db.commit()


@router.get("/shared/{token}", response_model=SharedGame)
def view_shared(token: str, db: Session = Depends(get_db)) -> SharedGame:
    """Public, unauthenticated read of a shared game.

    No auth dependency: possession of the token is the grant. Only the game is
    exposed — never the owner's contact details or their other games.
    """
    game = db.query(Game).filter(Game.share_token == token).one_or_none()
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is not valid.")

    owner = db.get(User, game.user_id)
    return SharedGame(
        white=game.white,
        black=game.black,
        result=game.result,
        pgn=game.pgn,
        accuracy_white=game.accuracy_white,
        accuracy_black=game.accuracy_black,
        shared_by=owner.display_name if owner else None,
        moves_san=[m.san for m in sorted(game.moves, key=lambda x: x.ply)],
    )


# ---------- Follows ----------

@router.post("/follow/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def follow(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    if user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot follow yourself.")
    if db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    exists = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.following_id == user_id)
        .first()
    )
    if not exists:  # idempotent
        db.add(Follow(follower_id=user.id, following_id=user_id))
        db.commit()


@router.delete("/follow/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.following_id == user_id)
        .one_or_none()
    )
    if row:
        db.delete(row)
        db.commit()


@router.get("/players", response_model=list[PublicProfile])
def players(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PublicProfile]:
    """Discover other players (excluding yourself)."""
    following_ids = {
        f.following_id
        for f in db.query(Follow).filter(Follow.follower_id == user.id).all()
    }
    rows = db.query(User).filter(User.id != user.id).limit(50).all()
    return [_profile(db, u, following_ids) for u in rows]


@router.get("/players/{user_id}", response_model=PublicProfile)
def player(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PublicProfile:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    following_ids = {
        f.following_id
        for f in db.query(Follow).filter(Follow.follower_id == user.id).all()
    }
    return _profile(db, target, following_ids)


def _profile(db: Session, u: User, following_ids: set[int]) -> PublicProfile:
    followers = db.query(func.count(Follow.id)).filter(Follow.following_id == u.id).scalar() or 0
    following = db.query(func.count(Follow.id)).filter(Follow.follower_id == u.id).scalar() or 0
    games = db.query(func.count(Game.id)).filter(Game.user_id == u.id).scalar() or 0
    return PublicProfile(
        id=u.id,
        display_name=u.display_name,
        rating=u.rating,
        puzzle_rating=u.puzzle_rating,
        games_analyzed=games,
        followers=followers,
        following=following,
        is_following=u.id in following_ids,
    )


# ---------- Bookmarks ----------

@router.get("/bookmarks", response_model=list[BookmarkItem])
def list_bookmarks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Bookmark]:
    return (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )


@router.post("/bookmarks", response_model=BookmarkItem)
def add_bookmark(
    body: BookmarkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bookmark:
    existing = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == user.id,
            Bookmark.entity_type == body.entity_type,
            Bookmark.entity_id == body.entity_id,
        )
        .one_or_none()
    )
    if existing:
        return existing
    row = Bookmark(
        user_id=user.id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = db.get(Bookmark, bookmark_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found.")
    db.delete(row)
    db.commit()
