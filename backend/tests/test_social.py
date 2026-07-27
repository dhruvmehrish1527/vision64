"""Tests for social-feature invariants that must hold at the model level."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.follow import Follow
from app.models.user import User


@pytest.fixture()
def db():
    """An isolated in-memory database per test."""
    engine = create_engine("sqlite://")
    # SQLite needs foreign keys / checks enabled explicitly per connection.
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [User(clerk_id="a", display_name="A"), User(clerk_id="b", display_name="B")]
    )
    session.commit()
    yield session
    session.close()


def test_following_is_recorded(db):
    db.add(Follow(follower_id=1, following_id=2))
    db.commit()
    assert db.query(Follow).count() == 1


def test_duplicate_follow_is_rejected(db):
    db.add(Follow(follower_id=1, following_id=2))
    db.commit()
    db.add(Follow(follower_id=1, following_id=2))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_self_follow_is_rejected_by_check_constraint(db):
    db.add(Follow(follower_id=1, following_id=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_follow_is_directional(db):
    db.add(Follow(follower_id=1, following_id=2))
    db.commit()
    # A following B does not imply B following A.
    assert db.query(Follow).filter(Follow.follower_id == 2).count() == 0
