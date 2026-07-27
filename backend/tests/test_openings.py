"""Unit tests for opening identification and search."""

from __future__ import annotations

from app.services.openings import by_eco, identify, next_moves, search


def test_identifies_basic_opening():
    assert identify(["e4", "e5", "Nf3", "Nc6", "Bb5"])["name"].startswith("Ruy López")


def test_prefers_the_most_specific_match():
    # A full Najdorf move order must not stop at "Sicilian Defence".
    najdorf = ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]
    assert identify(najdorf)["eco"] == "B90"
    # ...while the bare first move still resolves to the general Sicilian.
    assert identify(["e4", "c5"])["eco"] == "B20"


def test_identification_ignores_check_and_mate_marks():
    # Fried Liver ends ...Nxf7; decorations elsewhere must not break matching.
    line = ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6", "Ng5", "d5", "exd5", "Nxd5", "Nxf7"]
    assert identify(line)["eco"] == "C57"


def test_unknown_line_returns_none():
    assert identify(["a3", "h6", "a4"]) is None


def test_extra_moves_beyond_the_book_still_match():
    assert identify(["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4"])["eco"] == "C60"


def test_search_by_name_and_eco():
    assert any("Sicilian" in o["name"] for o in search("sicilian"))
    assert search("B90")[0]["eco"] == "B90"


def test_search_empty_returns_a_page():
    assert len(search("", limit=5)) == 5


def test_by_eco_is_case_insensitive():
    assert by_eco("c60")["name"].startswith("Ruy López")
    assert by_eco("ZZ9") is None


def test_next_moves_lists_continuations():
    moves = [c["move"] for c in next_moves(["e4"])]
    assert "e5" in moves and "c5" in moves


def test_every_opening_has_coaching_content():
    # The whole point of this dataset: no entry is just a move order.
    for o in search("", limit=999):
        assert o["plans"] and o["mistakes"] and o["famous"]
        assert o["white_win"] + o["draw"] + o["black_win"] == 100
