// Puzzle trainer.
//
// Serves weakness-targeted puzzles and lets the user solve them interactively:
// each dragged move is validated against the hidden solution on the backend,
// the opponent's reply is auto-played, and the puzzle rating updates on
// completion. The solution is only revealed on a wrong move.

import { Chess, type Square } from "chess.js";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { Chessboard } from "react-chessboard";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import type { Puzzle } from "@/types";

type Phase = "loading" | "solving" | "solved" | "failed";

const THEMES = [
  { value: "", label: "My weaknesses" },
  { value: "mate_in_1", label: "Mate in 1" },
  { value: "mate_in_2", label: "Mate in 2" },
  { value: "fork", label: "Forks" },
  { value: "win_material", label: "Win material" },
  { value: "tactic", label: "Tactics" },
  { value: "endgame", label: "Endgames" },
];

export function PuzzlePage() {
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [fen, setFen] = useState("");
  const [phase, setPhase] = useState<Phase>("loading");
  // A training-plan week can deep-link here with ?theme=… to drill that topic.
  const [searchParams, setSearchParams] = useSearchParams();
  const [theme, setTheme] = useState(searchParams.get("theme") ?? "");
  const [moveIndex, setMoveIndex] = useState(0);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [puzzleRating, setPuzzleRating] = useState<number | null>(null);
  const [solvedCount, setSolvedCount] = useState(0);
  const [attemptCount, setAttemptCount] = useState(0);
  const startTime = useRef<number>(Date.now());
  const preMoveFen = useRef<string>("");

  const load = useCallback((t: string) => {
    setPhase("loading");
    setFeedback(null);
    setMoveIndex(0);
    api
      .nextPuzzle(t || undefined)
      .then((p) => {
        setPuzzle(p);
        setFen(p.fen);
        setPhase("solving");
        startTime.current = Date.now();
      })
      .catch((e: ApiError) => setFeedback(e.message));
  }, []);

  useEffect(() => {
    load(theme);
  }, [theme, load]);

  const applyMove = (currentFen: string, uci: string): string => {
    const g = new Chess(currentFen);
    g.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4) || "q" });
    return g.fen();
  };

  const onDrop = useCallback(
    (from: Square, to: Square): boolean => {
      if (!puzzle || phase !== "solving") return false;

      // Validate legality locally first so illegal drags just snap back.
      const g = new Chess(fen);
      let uci: string;
      try {
        const m = g.move({ from, to, promotion: "q" });
        if (!m) return false;
        uci = `${m.from}${m.to}${m.promotion ?? ""}`;
      } catch {
        return false;
      }

      preMoveFen.current = fen;
      setFen(g.fen()); // show the move immediately; revert if it's wrong

      api
        .submitPuzzleMove(puzzle.id, moveIndex, uci, Date.now() - startTime.current)
        .then((res) => {
          if (!res.correct) {
            setPhase("failed");
            setAttemptCount((n) => n + 1);
            setFeedback("Not quite — here's the idea.");
            // Reveal the full solution by replaying it from the start.
            if (res.solution_uci) revealSolution(puzzle.fen, res.solution_uci);
            return;
          }
          if (res.solved) {
            setPhase("solved");
            setSolvedCount((n) => n + 1);
            setAttemptCount((n) => n + 1);
            if (res.new_puzzle_rating) setPuzzleRating(res.new_puzzle_rating);
            setFeedback("Solved! 🎉");
            return;
          }
          // Correct but not finished: auto-play the opponent's reply.
          setFeedback("Correct — keep going.");
          if (res.opponent_reply_uci) {
            setTimeout(() => {
              setFen((f) => applyMove(f, res.opponent_reply_uci!));
              setMoveIndex((i) => i + 1);
            }, 350);
          }
        })
        .catch(() => {
          setFen(preMoveFen.current);
          setFeedback("Something went wrong. Try the next puzzle.");
        });
      return true;
    },
    [puzzle, phase, fen, moveIndex]
  );

  const revealSolution = (startFen: string, solution: string[]) => {
    let f = startFen;
    solution.forEach((uci, i) => {
      setTimeout(() => setFen((f = applyMove(f, uci))), 500 * (i + 1));
    });
  };

  const accuracy = attemptCount > 0 ? Math.round((100 * solvedCount) / attemptCount) : null;

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="aspect-square w-full overflow-hidden rounded-2xl shadow-2xl ring-1 ring-white/10">
          {fen && (
            <Chessboard
              position={fen}
              onPieceDrop={(s, t) => onDrop(s as Square, t as Square)}
              boardOrientation={puzzle?.side_to_move ?? "white"}
              arePiecesDraggable={phase === "solving"}
              customDarkSquareStyle={{ backgroundColor: "#739552" }}
              customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
              customBoardStyle={{ borderRadius: "1rem" }}
              animationDuration={250}
            />
          )}
        </div>

        <AnimatePresence>
          {feedback && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`rounded-xl px-4 py-3 text-sm font-semibold ${
                phase === "solved"
                  ? "bg-emerald-500/15 text-emerald-300"
                  : phase === "failed"
                    ? "bg-red-500/15 text-red-300"
                    : "bg-white/5 text-slate-200"
              }`}
            >
              {feedback}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="space-y-4">
        <div className="card p-4">
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Puzzle theme
          </label>
          <select
            value={theme}
            onChange={(e) => {
              setTheme(e.target.value);
              setSearchParams(e.target.value ? { theme: e.target.value } : {});
            }}
            className="w-full rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm"
          >
            {THEMES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {puzzle && (
          <div className="card p-4">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-sm font-bold text-slate-200">
                {puzzle.side_to_move === "white" ? "White" : "Black"} to move
              </span>
              <span className="rounded-full bg-brand-500/15 px-2 py-0.5 text-xs font-semibold text-brand-400">
                {puzzle.theme.replace(/_/g, " ")}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Find the best {puzzle.player_move_count > 1 ? `${puzzle.player_move_count} moves` : "move"} · rated {puzzle.rating}
            </p>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <div className="card p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400">Rating</p>
            <p className="text-xl font-extrabold">{puzzleRating ?? "—"}</p>
          </div>
          <div className="card p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400">Solved</p>
            <p className="text-xl font-extrabold">{solvedCount}</p>
          </div>
          <div className="card p-3 text-center">
            <p className="text-[10px] uppercase tracking-wide text-slate-400">Accuracy</p>
            <p className="text-xl font-extrabold">{accuracy !== null ? `${accuracy}%` : "—"}</p>
          </div>
        </div>

        {(phase === "solved" || phase === "failed") && (
          <button onClick={() => load(theme)} className="btn-primary w-full">
            Next puzzle →
          </button>
        )}
        {phase === "loading" && (
          <p className="text-center text-sm text-slate-500">Loading puzzle…</p>
        )}
      </div>
    </div>
  );
}
