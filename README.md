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
| **Analysis board** | Drag pieces, import PGN/FEN, step through history, flip, undo/redo |
| **Engine** | Best move, top-5 candidates, eval bar, depth, principal variation, mate detection |
| **AI Coach** | Rating-adaptive natural-language explanations of tactics, strategy, plans, and typical mistakes |
| **Move classification** | Brilliant → Blunder, each with a plain-English reason |
| **Game review** | Accuracy score, turning points, phase-by-phase review, full coaching report |
| **Weakness tracker** | Detects recurring patterns (missed forks, hanging pieces, king safety…) |
| **Training plan** | Auto-generated weekly improvement plan that adapts to progress |
| **Puzzles** | Weakness-targeted puzzles with accuracy tracking |
| **Dashboard** | Rating, accuracy trends, streaks, most-common mistakes, interactive charts |

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

## 🧪 Tests

```bash
cd backend && pytest
```

---

## 📦 Project status

This repository is built in phases (see `ARCHITECTURE.md` → *Delivery phases*).
The current foundation ships a runnable engine + AI-coach + analysis board core;
subsequent phases layer on game review, weakness tracking, puzzles, and the
social dashboard.
