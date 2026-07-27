// The interactive analysis board — the app's core screen.
//
// Wires the board (react-chessboard) to the engine and AI coach:
//  - On every position change we ask the backend for the eval, best move, and
//    top-5 candidates (fast, no LLM) and draw the best-move arrow.
//  - When the user *plays* a move, we additionally classify it and stream a
//    rating-adaptive coaching explanation into the CoachPanel.
//  - Full history navigation, undo/redo, flip, and PGN/FEN import come from
//    the useChessGame hook; arrow keys and `f` are bound for keyboard control.

import { useCallback, useEffect, useRef, useState } from "react";
import { Chessboard } from "react-chessboard";
import type { Square } from "chess.js";

import { BoardControls } from "@/components/BoardControls";
import { CandidateMoves } from "@/components/CandidateMoves";
import { CoachPanel } from "@/components/CoachPanel";
import { EvalBar } from "@/components/EvalBar";
import { ImportDialog } from "@/components/ImportDialog";
import { MoveList } from "@/components/MoveList";
import { useChessGame } from "@/hooks/useChessGame";
import { api, ApiError, coachStream } from "@/lib/api";
import type { Classification, EngineResult } from "@/types";

export function AnalysisPage() {
  const game = useChessGame();
  const [engine, setEngine] = useState<EngineResult | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  const [rating, setRating] = useState(1000);

  const [coachLoading, setCoachLoading] = useState(false);
  const [coachError, setCoachError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [lastClassification, setLastClassification] = useState<Classification | null>(null);
  const [classifications, setClassifications] = useState<Record<number, Classification>>({});

  const [importOpen, setImportOpen] = useState(false);
  const reqId = useRef(0);

  // Analyse the current position whenever it changes (engine only — fast).
  useEffect(() => {
    const id = ++reqId.current;
    setEngineError(null);
    api
      .analysePosition(game.currentFen, { multipv: 5, depth: 16 })
      .then((res) => {
        if (id === reqId.current) setEngine(res.engine);
      })
      .catch((err: ApiError) => {
        if (id === reqId.current) {
          setEngine(null);
          setEngineError(
            err.status === 503
              ? "Engine offline — start Stockfish on the backend to see evaluations."
              : err.message
          );
        }
      });
  }, [game.currentFen]);

  // Handle a piece drop: make the move, then classify + explain it.
  const onDrop = useCallback(
    (from: Square, to: Square): boolean => {
      const before = game.currentFen;
      const ok = game.makeMove(from, to);
      if (!ok) return false;

      const uci = `${from}${to}`;
      const ply = game.cursor + 2;
      setCoachLoading(true);
      setCoachError(null);
      setExplanation("");
      setLastClassification(null);

      // Stream: classification arrives first (instant), then coaching text token
      // by token so the panel feels alive rather than blocking on the LLM.
      coachStream
        .move(before, uci, rating, {
          onMeta: (c) => {
            setCoachLoading(false);
            setLastClassification(c);
            setClassifications((prev) => ({ ...prev, [ply]: c }));
          },
          onText: (chunk) => setExplanation((prev) => (prev ?? "") + chunk),
          onError: (msg) => setCoachError(msg),
        })
        .catch((err: ApiError) =>
          setCoachError(
            err.status === 503
              ? "Coach or engine offline. Configure ANTHROPIC_API_KEY and Stockfish."
              : err.message
          )
        )
        .finally(() => setCoachLoading(false));
      return true;
    },
    [game, rating]
  );

  const explainPosition = useCallback(() => {
    setCoachLoading(true);
    setCoachError(null);
    setLastClassification(null);
    setExplanation("");
    coachStream
      .position(game.currentFen, rating, {
        onText: (chunk) => {
          setCoachLoading(false);
          setExplanation((prev) => (prev ?? "") + chunk);
        },
        onError: (msg) => setCoachError(msg),
      })
      .catch((err: ApiError) => setCoachError(err.message))
      .finally(() => setCoachLoading(false));
  }, [game.currentFen, rating]);

  // Keyboard navigation.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      if (e.key === "ArrowLeft") game.prev();
      else if (e.key === "ArrowRight") game.next();
      else if (e.key === "Home") game.first();
      else if (e.key === "End") game.last();
      else if (e.key.toLowerCase() === "f") game.flip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [game]);

  // Best-move arrow (react-chessboard expects [from, to, color] Square tuples).
  const arrows: [Square, Square, string][] =
    engine?.best_move && engine.best_move.length >= 4
      ? [
          [
            engine.best_move.slice(0, 2) as Square,
            engine.best_move.slice(2, 4) as Square,
            "#22c55e",
          ],
        ]
      : [];

  return (
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[1fr_360px]">
      {/* Left: board + controls */}
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className="h-[min(70vh,560px)]">
            <EvalBar
              evalCp={engine?.eval_cp ?? null}
              mateIn={engine?.mate_in ?? null}
              orientation={game.orientation}
            />
          </div>
          <div className="flex-1">
            <div className="aspect-square w-full overflow-hidden rounded-2xl shadow-2xl ring-1 ring-white/10">
              <Chessboard
                position={game.currentFen}
                onPieceDrop={(s, t) => onDrop(s as Square, t as Square)}
                boardOrientation={game.orientation}
                customArrows={arrows}
                customBoardStyle={{ borderRadius: "1rem" }}
                customDarkSquareStyle={{ backgroundColor: "#739552" }}
                customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
                animationDuration={200}
              />
            </div>
          </div>
        </div>

        <BoardControls
          canPrev={game.canPrev}
          canNext={game.canNext}
          onFirst={game.first}
          onPrev={game.prev}
          onNext={game.next}
          onLast={game.last}
          onFlip={game.flip}
          onImport={() => setImportOpen(true)}
        />

        {engineError && (
          <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 px-4 py-2 text-sm text-orange-200">
            {engineError}
          </div>
        )}
      </div>

      {/* Right: rating, coach, candidates, moves */}
      <div className="space-y-4">
        <div className="card flex items-center justify-between p-4">
          <label htmlFor="rating" className="text-sm font-semibold text-slate-300">
            Coaching level
          </label>
          <select
            id="rating"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
            className="rounded-lg border border-white/10 bg-ink-900 px-3 py-1.5 text-sm"
          >
            <option value={800}>Beginner (600–1000)</option>
            <option value={1200}>Club (1000–1400)</option>
            <option value={1600}>Intermediate (1400–1800)</option>
            <option value={2000}>Advanced (1800–2200)</option>
          </select>
        </div>

        <CoachPanel
          loading={coachLoading}
          classification={lastClassification}
          explanation={explanation}
          error={coachError}
        />

        <button onClick={explainPosition} className="btn-ghost w-full">
          💡 Explain this position
        </button>

        <CandidateMoves candidates={engine?.candidates ?? []} depth={engine?.depth ?? null} />

        <div className="card">
          <div className="border-b border-white/10 px-4 py-2 text-sm font-bold uppercase tracking-wide text-slate-300">
            Moves
          </div>
          <MoveList
            history={game.history}
            cursor={game.cursor}
            classifications={classifications}
            onSelect={game.goTo}
          />
        </div>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onLoadPgn={game.loadPgn}
        onLoadFen={game.loadFen}
      />
    </div>
  );
}
