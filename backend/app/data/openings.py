"""Curated opening database.

Each entry carries what a *learner* needs — not just the move order:

* `eco` / `name` — standard ECO classification and the opening's common name.
* `moves` — the defining line in SAN. Used to identify an opening from a game
  and to replay it on the board.
* `plans` — the typical middlegame plans for the side that chose it.
* `mistakes` — the errors players actually make in this structure.
* `famous` — well-known practitioners, so a learner can go study real games.
* `white_win` / `draw` / `black_win` — approximate master-level results (%),
  giving a feel for how the opening scores.

This is a hand-curated set covering the openings a 600–2200 player will
actually meet, rather than a giant machine-generated ECO dump: every entry has
real coaching content attached. It is a static Python module (no DB round-trip)
because it is read-only reference data.
"""

from __future__ import annotations

OPENINGS: list[dict] = [
    # ---------------- 1.e4 e5 — Open games ----------------
    {
        "eco": "C60", "name": "Ruy López (Spanish Opening)",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"],
        "white_win": 38, "draw": 38, "black_win": 24,
        "plans": [
            "Pressure the e5-pawn by pinning the knight that defends it.",
            "Build the big centre with c3 and d4 after retreating the bishop.",
            "Manoeuvre the b1-knight via d2–f1–g3 toward the kingside.",
        ],
        "mistakes": [
            "Grabbing the e5-pawn too early — after Bxc6 dxc6 Nxe5, Qd4 wins it back.",
            "Letting Black play ...b5 and ...Na5 to trade off your strong bishop for free.",
        ],
        "famous": ["Bobby Fischer", "Garry Kasparov", "Magnus Carlsen"],
    },
    {
        "eco": "C50", "name": "Italian Game",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4"],
        "white_win": 37, "draw": 36, "black_win": 27,
        "plans": [
            "Aim the bishop at f7, Black's weakest square early on.",
            "Play c3 and d4 to seize the centre.",
            "Castle quickly and bring a rook to e1.",
        ],
        "mistakes": [
            "Playing Ng5 too early — after ...d5 Black often gets good counterplay.",
            "Forgetting that the c4-bishop can be shut out by ...d5.",
        ],
        "famous": ["Giuoco Piano masters", "Anatoly Karpov", "Hikaru Nakamura"],
    },
    {
        "eco": "C57", "name": "Two Knights Defence — Fried Liver Attack",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6", "Ng5", "d5", "exd5", "Nxd5", "Nxf7"],
        "white_win": 45, "draw": 20, "black_win": 35,
        "plans": [
            "Sacrifice on f7 to drag the black king into the open.",
            "Follow up with Qf3+ and Nc3 hitting the loose d5-knight.",
        ],
        "mistakes": [
            "As Black, recapturing with ...Nxd5 walks into the sacrifice — ...Na5! is safer.",
            "As White, playing the sacrifice without calculating Qf3+ and Nc3 first.",
        ],
        "famous": ["Polerio (1600s)", "Club players everywhere"],
    },
    {
        "eco": "C23", "name": "Bishop's Opening",
        "moves": ["e4", "e5", "Bc4"],
        "white_win": 36, "draw": 35, "black_win": 29,
        "plans": ["Target f7 immediately.", "Transpose into Italian or Vienna structures."],
        "mistakes": ["Developing the queen early and losing time to ...Nf6."],
        "famous": ["Larry Kaufman", "Vasyl Ivanchuk"],
    },
    {
        "eco": "C20", "name": "King's Pawn Game",
        "moves": ["e4", "e5"],
        "white_win": 37, "draw": 35, "black_win": 28,
        "plans": ["Fight for the centre and develop toward quick castling."],
        "mistakes": ["Moving the same piece repeatedly instead of developing."],
        "famous": ["Every player, at some point"],
    },
    {
        "eco": "C30", "name": "King's Gambit",
        "moves": ["e4", "e5", "f4"],
        "white_win": 36, "draw": 30, "black_win": 34,
        "plans": [
            "Give up a pawn to rip open the f-file and seize the centre with d4.",
            "Attack quickly before Black consolidates the extra pawn.",
        ],
        "mistakes": [
            "Playing it slowly — the gambit needs energy or the pawn just stays lost.",
            "As Black, greedily holding the pawn with ...g5 and getting the king caught.",
        ],
        "famous": ["Adolf Anderssen", "Paul Morphy", "Hikaru Nakamura"],
    },
    {
        "eco": "C41", "name": "Philidor Defence",
        "moves": ["e4", "e5", "Nf3", "d6"],
        "white_win": 40, "draw": 33, "black_win": 27,
        "plans": ["Solid but passive; Black aims for ...Nf6, ...Be7 and a later ...d5 break."],
        "mistakes": ["Blocking the f8-bishop and never freeing the position."],
        "famous": ["François-André Philidor", "Étienne Bacrot"],
    },
    {
        "eco": "C42", "name": "Petrov (Russian) Defence",
        "moves": ["e4", "e5", "Nf3", "Nf6"],
        "white_win": 34, "draw": 45, "black_win": 21,
        "plans": ["Mirror White's play and simplify toward equality."],
        "mistakes": ["Taking on e4 immediately — 3...Nxe4 4.Qe2 costs material after ...Nf6??"],
        "famous": ["Vladimir Kramnik", "Fabiano Caruana"],
    },
    {
        "eco": "C00", "name": "French Defence",
        "moves": ["e4", "e6"],
        "white_win": 37, "draw": 34, "black_win": 29,
        "plans": [
            "Strike at the centre with ...d5 and later ...c5.",
            "Play on the queenside where Black's pawn chain points.",
        ],
        "mistakes": [
            "Leaving the light-squared bishop trapped behind the pawn chain.",
            "As White, over-extending with e5 and losing the d4-pawn to ...c5 pressure.",
        ],
        "famous": ["Viktor Korchnoi", "Wesley So", "Alexander Morozevich"],
    },
    {
        "eco": "B20", "name": "Sicilian Defence",
        "moves": ["e4", "c5"],
        "white_win": 37, "draw": 33, "black_win": 30,
        "plans": [
            "Trade a flank pawn for a centre pawn and play on the half-open c-file.",
            "Counter-attack on the queenside while White attacks the king.",
        ],
        "mistakes": [
            "Playing passively — the Sicilian punishes players who don't seek counterplay.",
            "Neglecting development while grabbing pawns.",
        ],
        "famous": ["Garry Kasparov", "Bobby Fischer", "Magnus Carlsen"],
    },
    {
        "eco": "B90", "name": "Sicilian Najdorf",
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
        "white_win": 38, "draw": 33, "black_win": 29,
        "plans": [
            "...a6 prepares ...e5 or ...b5 without allowing Nb5.",
            "Fight for the d5-square and expand on the queenside.",
        ],
        "mistakes": ["Playing ...e5 before it's prepared, leaving a permanent d5 hole."],
        "famous": ["Bobby Fischer", "Garry Kasparov", "Miguel Najdorf"],
    },
    {
        "eco": "B10", "name": "Caro-Kann Defence",
        "moves": ["e4", "c6"],
        "white_win": 36, "draw": 39, "black_win": 25,
        "plans": [
            "Support ...d5 with the c-pawn, keeping a sound structure.",
            "Develop the light-squared bishop *outside* the pawn chain before ...e6.",
        ],
        "mistakes": ["Playing ...e6 first and burying the c8-bishop — the classic Caro error."],
        "famous": ["Anatoly Karpov", "Tigran Petrosian", "Fabiano Caruana"],
    },
    {
        "eco": "B01", "name": "Scandinavian Defence",
        "moves": ["e4", "d5"],
        "white_win": 40, "draw": 32, "black_win": 28,
        "plans": ["Trade centre pawns immediately and develop with tempo-safe queen moves."],
        "mistakes": ["Letting the queen get chased around after ...Qxd5 — retreat to a5 or d6."],
        "famous": ["Bent Larsen", "Magnus Carlsen (occasionally)"],
    },
    {
        "eco": "B07", "name": "Pirc Defence",
        "moves": ["e4", "d6", "d4", "Nf6", "Nc3", "g6"],
        "white_win": 40, "draw": 32, "black_win": 28,
        "plans": ["Let White build a centre, then undermine it with ...c5 or ...e5."],
        "mistakes": ["Allowing a full pawn roller (e4-d4-f4) without counter-striking in time."],
        "famous": ["Vasja Pirc", "Alexander Beliavsky"],
    },
    {
        "eco": "C44", "name": "Scotch Game",
        "moves": ["e4", "e5", "Nf3", "Nc6", "d4"],
        "white_win": 38, "draw": 34, "black_win": 28,
        "plans": ["Open the centre at once and develop with tempo."],
        "mistakes": ["Recapturing on d4 with the queen too early and losing time to ...Nc6."],
        "famous": ["Garry Kasparov", "Ian Nepomniachtchi"],
    },
    # ---------------- 1.d4 — Closed games ----------------
    {
        "eco": "D06", "name": "Queen's Gambit",
        "moves": ["d4", "d5", "c4"],
        "white_win": 39, "draw": 37, "black_win": 24,
        "plans": [
            "Trade the c-pawn for the centre and dominate with e4 later.",
            "Use the half-open c-file for a minority attack.",
        ],
        "mistakes": ["Trying to hold the gambit pawn with ...b5 — it loses material to a3 and axb4."],
        "famous": ["José Raúl Capablanca", "Anatoly Karpov", "Ding Liren"],
    },
    {
        "eco": "D30", "name": "Queen's Gambit Declined",
        "moves": ["d4", "d5", "c4", "e6"],
        "white_win": 38, "draw": 40, "black_win": 22,
        "plans": ["Hold the centre solidly and free the game with ...c5 or ...dxc4 and ...c5."],
        "mistakes": ["Leaving the c8-bishop passive for too long."],
        "famous": ["Anatoly Karpov", "Vladimir Kramnik"],
    },
    {
        "eco": "D10", "name": "Slav Defence",
        "moves": ["d4", "d5", "c4", "c6"],
        "white_win": 37, "draw": 41, "black_win": 22,
        "plans": ["Support d5 with the c-pawn while keeping the c8-bishop's diagonal open."],
        "mistakes": ["Grabbing on c4 without the follow-up ...b5 and ...Bb7 idea."],
        "famous": ["Vladimir Kramnik", "Viswanathan Anand"],
    },
    {
        "eco": "E60", "name": "King's Indian Defence",
        "moves": ["d4", "Nf6", "c4", "g6"],
        "white_win": 39, "draw": 31, "black_win": 30,
        "plans": [
            "Concede the centre, fianchetto, then storm the kingside with ...f5–f4 and ...g5.",
            "Accept a space disadvantage in return for a fierce attack.",
        ],
        "mistakes": ["Opening the centre while behind in space — it favours White."],
        "famous": ["Garry Kasparov", "Bobby Fischer", "Teimour Radjabov"],
    },
    {
        "eco": "E20", "name": "Nimzo-Indian Defence",
        "moves": ["d4", "Nf6", "c4", "e6", "Nc3", "Bb4"],
        "white_win": 36, "draw": 40, "black_win": 24,
        "plans": ["Pin the c3-knight, double White's pawns, and blockade on the light squares."],
        "mistakes": ["Giving up the bishop pair too cheaply without damaging the structure."],
        "famous": ["Aron Nimzowitsch", "Anatoly Karpov", "Levon Aronian"],
    },
    {
        "eco": "A45", "name": "Indian Defence",
        "moves": ["d4", "Nf6"],
        "white_win": 38, "draw": 36, "black_win": 26,
        "plans": ["Control e4 with pieces before committing pawns."],
        "mistakes": ["Drifting without a plan and letting White take the whole centre."],
        "famous": ["Hypermodern school"],
    },
    {
        "eco": "D80", "name": "Grünfeld Defence",
        "moves": ["d4", "Nf6", "c4", "g6", "Nc3", "d5"],
        "white_win": 38, "draw": 36, "black_win": 26,
        "plans": ["Let White build a big centre, then dismantle it with ...c5 and pressure on d4."],
        "mistakes": ["Trading into a passive endgame instead of hitting the centre quickly."],
        "famous": ["Ernst Grünfeld", "Garry Kasparov", "Ding Liren"],
    },
    {
        "eco": "A80", "name": "Dutch Defence",
        "moves": ["d4", "f5"],
        "white_win": 41, "draw": 30, "black_win": 29,
        "plans": ["Grab kingside space and aim for a ...e5 break or a direct attack."],
        "mistakes": ["Weakening the e8–h5 diagonal — watch for Qh5+ tricks early."],
        "famous": ["Mikhail Botvinnik", "Simon Williams"],
    },
    {
        "eco": "A40", "name": "Queen's Pawn Game",
        "moves": ["d4"],
        "white_win": 38, "draw": 37, "black_win": 25,
        "plans": ["Occupy the centre and develop flexibly."],
        "mistakes": ["Automatic moves without deciding on a structure."],
        "famous": ["Universal"],
    },
    # ---------------- Flank / other ----------------
    {
        "eco": "A10", "name": "English Opening",
        "moves": ["c4"],
        "white_win": 38, "draw": 38, "black_win": 24,
        "plans": ["Control d5 from the flank and transpose favourably to d4 structures."],
        "mistakes": ["Playing it as a 'quiet' opening and neglecting the centre entirely."],
        "famous": ["Mikhail Botvinnik", "Magnus Carlsen"],
    },
    {
        "eco": "A04", "name": "Réti Opening",
        "moves": ["Nf3"],
        "white_win": 37, "draw": 39, "black_win": 24,
        "plans": ["Develop first, commit pawns later; invite Black to over-extend."],
        "mistakes": ["Being too passive and letting Black build an ideal centre for free."],
        "famous": ["Richard Réti", "Vladimir Kramnik"],
    },
    {
        "eco": "A00", "name": "Bird's Opening",
        "moves": ["f4"],
        "white_win": 35, "draw": 33, "black_win": 32,
        "plans": ["Control e5 and play a reversed Dutch with an extra tempo."],
        "mistakes": ["Weakening the king early — beware ...e5 gambits and Qh4+ ideas."],
        "famous": ["Henry Bird", "Bent Larsen"],
    },
    {
        "eco": "B00", "name": "Nimzowitsch Defence",
        "moves": ["e4", "Nc6"],
        "white_win": 42, "draw": 30, "black_win": 28,
        "plans": ["Provoke White forward, then hit the centre with ...d5 or ...e5."],
        "mistakes": ["Letting White gain space with d4-d5 kicking the knight around."],
        "famous": ["Aron Nimzowitsch", "Tony Miles"],
    },
    {
        "eco": "C21", "name": "Danish Gambit",
        "moves": ["e4", "e5", "d4", "exd4", "c3"],
        "white_win": 40, "draw": 26, "black_win": 34,
        "plans": ["Sacrifice up to two pawns for raking bishops on the a2–g8 and a1–h8 diagonals."],
        "mistakes": ["As Black, greedily taking everything and falling far behind in development."],
        "famous": ["Martin Severin From", "19th-century romantics"],
    },
    {
        "eco": "C46", "name": "Four Knights Game",
        "moves": ["e4", "e5", "Nf3", "Nc6", "Nc3", "Nf6"],
        "white_win": 35, "draw": 41, "black_win": 24,
        "plans": ["Symmetrical and solid; play for a small edge with d4 or Bb5."],
        "mistakes": ["Assuming symmetry means a draw and playing without ambition."],
        "famous": ["Classical masters"],
    },
]


def all_openings() -> list[dict]:
    return OPENINGS
