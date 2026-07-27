"""Opening identification and search.

Identification walks the played move list against the curated database and keeps
the **longest** matching prefix — so 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 Nf6 5.Nc3 a6
resolves to the Najdorf rather than stopping at "Sicilian Defence". Matching is
done on SAN, which is what both the PGN parser and the frontend produce.
"""

from __future__ import annotations

from app.data.openings import OPENINGS


def _normalize(san: str) -> str:
    """Ignore check/mate marks so 'Qh4#' and 'Qh4' compare equal."""
    return san.rstrip("+#")


def identify(moves_san: list[str]) -> dict | None:
    """Return the most specific opening whose line prefixes the given moves."""
    played = [_normalize(m) for m in moves_san]
    best: dict | None = None
    for entry in OPENINGS:
        line = [_normalize(m) for m in entry["moves"]]
        if len(line) > len(played):
            continue
        if played[: len(line)] == line:
            if best is None or len(line) > len(best["moves"]):
                best = entry
    return best


def search(query: str, limit: int = 20) -> list[dict]:
    """Search by opening name or ECO code (case-insensitive substring)."""
    q = (query or "").strip().lower()
    if not q:
        return OPENINGS[:limit]
    hits = [
        o for o in OPENINGS
        if q in o["name"].lower() or q in o["eco"].lower()
    ]
    # Name matches that start with the query rank first.
    hits.sort(key=lambda o: (not o["name"].lower().startswith(q), o["name"]))
    return hits[:limit]


def by_eco(eco: str) -> dict | None:
    target = (eco or "").strip().upper()
    return next((o for o in OPENINGS if o["eco"].upper() == target), None)


def next_moves(moves_san: list[str]) -> list[dict]:
    """Which continuations exist from here, for browsing the opening tree."""
    played = [_normalize(m) for m in moves_san]
    seen: dict[str, dict] = {}
    for entry in OPENINGS:
        line = [_normalize(m) for m in entry["moves"]]
        if len(line) <= len(played):
            continue
        if line[: len(played)] != played:
            continue
        nxt = entry["moves"][len(played)]
        # Keep the shallowest opening that starts with this continuation.
        if nxt not in seen or len(entry["moves"]) < len(seen[nxt]["moves"]):
            seen[nxt] = entry
    return [
        {"move": mv, "eco": o["eco"], "name": o["name"]}
        for mv, o in sorted(seen.items())
    ]
