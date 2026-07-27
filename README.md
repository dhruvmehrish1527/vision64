# ♞ Vision64

**A free, AI-powered chess coach that explains *why* moves are good or bad — not just what the engine plays.**

Vision64 pairs the Stockfish engine with Claude to turn raw engine output into
beginner-friendly, rating-adaptive coaching. It classifies every move, reviews
whole games, tracks your recurring weaknesses, and builds a personalized
training plan — the kind of premium learning experience usually locked behind
paid chess platforms.

> Built as a full-stack demonstration of software engineering, AI integration,
> algorithms, and user-centered design.

---

## ✨ Features

| Area | What it does |
|------|--------------|
| **Analysis board** | Drag pieces, import PGN/FEN, step through history, flip, keyboard shortcuts |
| **Engine** | Best move, top-5 candidates, eval bar, depth, principal variation, mate detection |
| **AI Coach** | Rating-adaptive explanations, **streamed token-by-token**, covering tactics, strategy, plans, and typical mistakes |
| **Move classification** | Brilliant → Blunder, each with a plain-English reason |
| **Game review** | Accuracy score, evaluation timeline, turning points, phase-by-phase breakdown |
| **Weakness tracker** | Detects recurring patterns (missed forks, hanging pieces, king safety…) |
| **Training plan** | Adaptive multi-week plan that re-plans as your weaknesses change |
| **Puzzles** | Engine-verified tactics, **auto-generated from your own blunders** |
| **AI opponent** | Play Stockfish at 4 strengths (~1320–2600), with post-game coaching |
| **Opening explorer** | ECO codes, win rates, typical plans, common mistakes, saved repertoires |
| **Dashboard** | Rating, accuracy, streaks, most-common mistakes, interactive charts |

### A note on the design

Move classification, accuracy, and weakness detection are **deterministic
algorithms** over engine output — reproducible, unit-tested, and free to run.
The LLM's only job is to *explain* a verdict Stockfish already justified. That
keeps coaching accurate (the numbers come from the engine), costs bounded, and
hallucinated evaluations out of the product.

---

## 🏗️ Architecture

```
vision64/
├── backend/      FastAPI · Python · SQLAlchemy · Alembic · Stockfish · Claude
├── frontend/     React · TypeScript · Vite · Tailwind · react-chessboard · Framer Motion
└── ARCHITECTURE.md   Design decisions, data model, request flow
```

Read **[ARCHITECTURE.md](./ARCHITECTURE.md)** first — it explains every major
design decision before you touch the code.

- Frontend deploys to **Vercel**
- Backend deploys to **Railway / Render**
- Database is **PostgreSQL**
- Auth is **Clerk** (JWT verified in FastAPI middleware)
- The AI coach runs on the **Claude API** (`claude-opus-5`)

---

## 🚀 Quick start

### Prerequisites

- Python 3.11+
- Node 20+
- PostgreSQL 15+ (or use the bundled SQLite fallback for local dev)
- Stockfish (`brew install stockfish` on macOS, `apt install stockfish` on Linux)
- A Clerk application + an `ANTHROPIC_API_KEY`

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in the values
alembic upgrade head          # create tables
uvicorn app.main:app --reload # http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # fill in VITE_* values
npm run dev                   # http://localhost:5173
```

---

> **Running without accounts:** leave `AUTH_DEV_BYPASS=true` and the app runs
> end-to-end with no Clerk project. Without an `ANTHROPIC_API_KEY` everything
> still works — the coach panel degrades gracefully to a clear message while the
> engine, classification, review, puzzles, and charts keep running.

---

## 🧪 Tests

```bash
cd backend && pytest
```

31 tests cover the deterministic core: move classification, PGN/FEN parsing,
training-plan generation, AI-opponent helpers, and opening identification.

---

## 🚢 Deployment

**Backend → Render** (Blueprint from `render.yaml`; the `Dockerfile` bundles
Stockfish and runs migrations on boot). **Frontend → Vercel** (root directory
`frontend/`).

Step-by-step instructions, the full environment-variable table, and a
post-deploy checklist are in **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

---

## 📦 Project status

Built in phases (see `ARCHITECTURE.md` → *Delivery phases*). Phases 1–6 are
complete and verified end-to-end: engine analysis, streaming AI coaching, game
review, weakness tracking, puzzles, training plans, the AI opponent, and the
opening explorer all run against a live Stockfish. Deployment configs are
included and ready to apply.
