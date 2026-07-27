"""Opening explorer endpoints: search, identify, browse, and save a repertoire."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.clerk import get_current_user
from app.db.session import get_db
from app.models.repertoire import RepertoireEntry
from app.models.user import User
from app.services.openings import by_eco, identify, next_moves, search

router = APIRouter(prefix="/openings", tags=["openings"])


class OpeningSchema(BaseModel):
    eco: str
    name: str
    moves: list[str]
    white_win: int
    draw: int
    black_win: int
    plans: list[str]
    mistakes: list[str]
    famous: list[str]


class IdentifyRequest(BaseModel):
    moves_san: list[str] = Field(default_factory=list)


class IdentifyResponse(BaseModel):
    opening: OpeningSchema | None
    continuations: list[dict] = []


class SaveRepertoireRequest(BaseModel):
    eco: str
    color: str = Field(default="white", description='"white" | "black"')
    note: str | None = None


class RepertoireItem(BaseModel):
    id: int
    eco: str
    name: str
    color: str
    note: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[OpeningSchema])
def list_openings(
    q: str = Query(default="", description="Search by name or ECO code."),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    """Search the opening database."""
    return search(q, limit=limit)


@router.get("/{eco}", response_model=OpeningSchema)
def get_opening(eco: str) -> dict:
    entry = by_eco(eco)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opening not found.")
    return entry


@router.post("/identify", response_model=IdentifyResponse)
def identify_opening(body: IdentifyRequest) -> IdentifyResponse:
    """Name the opening from a played move list, plus what can follow.

    Returns the *most specific* match, so a full Najdorf move order resolves to
    the Najdorf rather than stopping at "Sicilian Defence".
    """
    found = identify(body.moves_san)
    return IdentifyResponse(
        opening=OpeningSchema(**found) if found else None,
        continuations=next_moves(body.moves_san),
    )


@router.get("/me/repertoire", response_model=list[RepertoireItem])
def my_repertoire(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RepertoireEntry]:
    return (
        db.query(RepertoireEntry)
        .filter(RepertoireEntry.user_id == user.id)
        .order_by(RepertoireEntry.color, RepertoireEntry.eco)
        .all()
    )


@router.post("/me/repertoire", response_model=RepertoireItem)
def save_to_repertoire(
    body: SaveRepertoireRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RepertoireEntry:
    """Save an opening to the user's repertoire (idempotent per ECO+colour)."""
    entry = by_eco(body.eco)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opening not found.")
    color = "black" if body.color.lower() == "black" else "white"

    existing = (
        db.query(RepertoireEntry)
        .filter(
            RepertoireEntry.user_id == user.id,
            RepertoireEntry.eco == entry["eco"],
            RepertoireEntry.color == color,
        )
        .one_or_none()
    )
    if existing:
        existing.note = body.note or existing.note
        db.commit()
        db.refresh(existing)
        return existing

    row = RepertoireEntry(
        user_id=user.id,
        eco=entry["eco"],
        name=entry["name"],
        color=color,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/me/repertoire/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_repertoire(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = db.get(RepertoireEntry, entry_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found.")
    db.delete(row)
    db.commit()
