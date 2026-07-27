# Vision64 — Architecture

This document explains the design decisions behind Vision64 *before* the code,
so the "why" is legible to a reviewer. It covers the system shape, the data
model, the request flow through the engine + AI coach, and the phased delivery
plan.

---

## 1. Design principles

1. **The engine never speaks without a coach.** Every engine evaluation is
   wrapped in a human explanation. The `EngineService` and `CoachService` are
   separate modules, but the API composes them so a bare "best move: Nf3" is
   never returned to the client.
2. **Rating-adaptive teaching.** A 600-rated beginner and a 2000-rated
   improver need different explanations of the same position. The player's
   rating is a first-class input to the coach prompt.
3. **Deterministic core, generative shell.** Classification, accuracy, and
   weakness detection are *deterministic algorithms* over engine output
   (reproducible, testable, cheap). The natural-language layer is the only
   part that calls an LLM. This keeps costs bounded and behavior explainable.
4. **Stateless API, stateful database.** FastAPI handlers hold no session
   state; everything durable lives in PostgreSQL. This lets the backend scale
   horizontally on Railway/Render.
5. **Type safety end to end.** Pydantic schemas on the backend mirror
   TypeScript types on the frontend, generated from the same conceptual model.

---

## 2. System shape

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + TS + Vite + Tailwind)                         │
│                                                                  │
│  AnalysisBoard ── EvalBar ── MoveList ── CoachPanel ── Dashboard │
│        │  react-chessboard + chess.js maintain board state       │
│        │  Clerk provides auth; JWT attached to every API call    │
└────────┼─────────────────────────────────────────────────────────┘
         │ HTTPS (JSON) — Bearer <Clerk JWT>
┌────────▼─────────────────────────────────────────────────────────┐
│  FastAPI (Python)                                                │
│                                                                  │
│  auth/clerk.py ── verifies JWT, resolves/creates the User        │
│  api/routes/*  ── thin handlers, one per domain                  │
│        │                                                          │
│        ├── services/engine.py     (Stockfish over UCI)           │
│        ├── services/classifier.py (deterministic move labels)    │
│        ├── services/coach.py       (Claude → explanations)       │
│        ├── services/review.py      (whole-game report)           │
│        └── services/weakness.py    (pattern aggregation)         │
│        │                                                          │
│  db/ + models/ ── SQLAlchemy → PostgreSQL (Alembic migrations)   │
└────────┼──────────────────────────────────┬──────────────────────┘
         │                                   │
┌────────▼────────┐                 ┌────────▼────────┐
│  Stockfish UCI  │                 │   Claude API    │
│  (local binary) │                 │  (claude-opus-5)│
└─────────────────┘                 └─────────────────┘
```

### Why FastAPI + Python for the backend

Chess tooling lives in Python — `python-chess` is the reference library for
PGN/FEN parsing, legal-move generation, and UCI engine communication.
Co-locating the engine driver, the chess logic, and the API in one Python
service avoids a second language boundary. FastAPI gives us async I/O (engine
and LLM calls are both I/O-bound), automatic OpenAPI docs, and Pydantic
validation for free.

### Why a deterministic classifier separate from the LLM

Move classification (Blunder/Mistake/Brilliant/…) is defined by *centipawn
loss thresholds and tactical checks*, not by taste. Computing it
deterministically means:

- It is unit-testable and reproducible.
- It runs without an API call, so full-game review is cheap.
- The LLM's job narrows to *explaining* a label we already trust, which makes
  hallucinated evaluations far less likely.

---

## 3. Data model

```
User ─┬─< Game ─┬─< Move ──< MoveAnalysis
      │         └─── GameReview (1:1)
      │
      ├─── WeaknessProfile (1:1, JSON aggregate)
      ├─── TrainingPlan ──< TrainingWeek
      ├─< PuzzleAttempt >─ Puzzle
      └─< Bookmark
```

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `users` | One row per Clerk user | `clerk_id` (unique), `rating`, `puzzle_rating`, `streak_days`, `last_active` |
| `games` | An imported game or an analysis session | `pgn`, `initial_fen`, `result`, `source`, `accuracy_white`, `accuracy_black` |
| `moves` | One row per half-move | `ply`, `san`, `uci`, `fen_before`, `fen_after` |
| `move_analyses` | Engine + classification per move | `eval_cp`, `best_move`, `pv` (JSON), `depth`, `mate_in`, `classification`, `centipawn_loss`, `explanation` |
| `game_reviews` | Coaching report for a whole game | `accuracy`, `biggest_mistake_ply`, `phases` (JSON), `summary` |
| `weakness_profiles` | Rolling per-user aggregate | `patterns` (JSON: {missed_fork: 12, hanging_piece: 8, …}) |
| `training_plans` / `training_weeks` | Adaptive study plan | `week_number`, `focus_topics` (JSON), `completed` |
| `puzzles` | Generated/curated tactics | `fen`, `solution_uci` (JSON), `theme`, `rating` |
| `puzzle_attempts` | Per-user puzzle results | `correct`, `time_ms`, `attempted_at` |
| `bookmarks` | Saved games / lessons | `entity_type`, `entity_id` |

All timestamps are UTC. `move_analyses.explanation` is nullable — it is filled
lazily (only when a user asks the coach, or during a full review), so we never
pay for LLM tokens we don't display.

### JSON columns

`pv`, `phases`, `patterns`, `focus_topics`, `solution_uci` use PostgreSQL
`JSONB`. These are semi-structured and read-mostly; JSONB avoids a proliferation
of child tables for data we always fetch as a unit. On SQLite (local fallback)
they degrade to `JSON` transparently via SQLAlchemy's `JSON` type.

---

## 4. Request flow: analyzing a position

```
POST /api/analysis/position   { fen, rating, multipv=5 }
  │
  ├─ EngineService.analyse(fen, multipv, depth)
  │     → { eval_cp, mate_in, best_move, pv, candidates[5], depth }
  │
  ├─ ClassifierService.classify(prev_eval, this_eval, ...)   (if a move was made)
  │     → { label, centipawn_loss, tags[] }
  │
  └─ CoachService.explain(fen, engine_result, classification, rating)
        → natural-language explanation (Claude, adaptive to rating)

Response: EngineResult + Classification + Explanation, composed.
```

The coach call is the only external-latency step, so the API supports two
modes: `explain=false` returns engine + classification instantly for the eval
bar and arrows, and a follow-up `POST /api/analysis/explain` streams the
coaching text. This keeps the board responsive.

---

## 5. The AI coach

`CoachService` builds a structured prompt from engine facts and asks Claude for
an explanation calibrated to the player's rating band (600–1000, 1000–1400,
1400–1800, 1800–2200). The prompt is **grounded**: it passes the engine's
evaluation, best line, and the deterministic classification as facts, and asks
Claude to *explain* them rather than *invent* them. Every explanation is asked
to touch, where relevant: tactical ideas, strategic ideas, piece activity,
king safety, pawn structure, long-term plans, and the typical mistake at that
level.

Model: `claude-opus-5` with adaptive thinking. Prompt caching is applied to the
stable system prompt (the coaching rubric) so repeated calls are cheap.

---

## 6. Auth

Clerk issues a JWT on the frontend. Every API request carries it as
`Authorization: Bearer <jwt>`. `auth/clerk.py` verifies the token against
Clerk's JWKS, extracts the `sub` (Clerk user id), and upserts a local `User`
row. Handlers depend on `get_current_user`, so an unauthenticated request never
reaches business logic. This keeps Clerk as the identity source of truth while
letting us own user-scoped chess data locally.

---

## 7. Delivery phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Architecture, folder structure, DB schema | ✅ this doc + models + migrations |
| 2 | Backend: config, DB, auth, engine, classifier, coach, core routes | ✅ core shipped |
| 3 | Frontend: analysis board, eval bar, move list, coach panel | ✅ core shipped |
| 4 | Engine hardening — warm `EnginePool` (review 10s → 2.3s, ~4.4×) | ✅ |
| 5 | AI coaching depth — SSE streaming coach + full game-review UI | ✅ |
| 6 | Analytics — weakness tracker, puzzles, adaptive training plan | ✅ core |
| 7 | Deployment: Vercel + Railway/Render, CI | ⏳ |

### Engine pooling (Phase 4)

`EnginePool` keeps `ENGINE_POOL_SIZE` (default 3) Stockfish processes alive and
lends one per analysis. Opening a process plus the UCI handshake cost ~50–150 ms,
which dominated full-game review; pooling cut a 21-move review from ~10 s to
~2.3 s. `SimpleEngine` is single-threaded, so `acquire()` blocks until an engine
is free — this also caps concurrent CPU use. A crashed engine is transparently
replaced, and the pool is shut down on app exit so no process is orphaned.

### Adaptive training plan

`services/training.py` holds a `CURRICULUM` mapping each trainable weakness tag
to a goal, focus topics, and the puzzle theme that drills it. Weeks are ordered
by *impact* (how often the pattern actually cost the player) then by difficulty,
so the biggest cheap leak is fixed first; users with no data get universal
fundamentals. `POST /training/plan/regenerate` re-plans the unfinished weeks
against the current weakness profile while preserving completed ones, so
progress is never lost and the plan follows the player's improvement.

### AI opponent

Four named strengths map to Stockfish `UCI_Elo` targets (1320 / 1600 / 2000 /
2600). We use the engine's own strength limiter rather than a shallow search:
at low Elo Stockfish makes *plausible human mistakes* — it missed a Fool's Mate
at Beginner that Master found instantly — whereas a shallow-search bot plays
alien, random-looking moves. The weakened options are reset after every call so
a limited opponent never leaks into an analysis sharing the same pooled process.

Game state lives in the database as a `Game` plus its `Move` rows — the same
shape as an imported PGN — so an AI game survives restarts and can be fed
straight into the existing review pipeline for post-game coaching with no
special-casing.

### Puzzle generation

Puzzles come from two sources: engine-verified curated positions (seeded at
startup, and only kept when a genuine tactic exists) and the player's own
blunders — every reviewed game is automatically mined into personalized
"you missed this" puzzles, deduped by FEN, so the pool grows with use.

Each phase is additive and leaves the app runnable.

---

## 8. Non-functional decisions

- **Error handling**: services raise typed exceptions (`EngineUnavailable`,
  `CoachUnavailable`); handlers translate them to HTTP problem responses.
- **Logging**: structured logging via `structlog`-style config in
  `core/logging.py`; every engine and coach call logs latency.
- **Config**: 12-factor via `pydantic-settings`; nothing secret is hard-coded.
- **Security**: CORS locked to the known frontend origin, JWT verified on every
  request, no raw SQL, secrets only from the environment.
- **Testing**: `pytest` covers the classifier (pure functions) and the engine
  adapter (against a real Stockfish when present, skipped otherwise).
