// Play against the AI.
//
// Pick a strength and a colour, then play a full game against Stockfish limited
// to that Elo. Moves are validated locally for instant feedback and confirmed by
// the server, which also returns the AI's reply. When the game ends, one click
// runs the full review pipeline and returns coaching feedback on how you played.

import { Chess, type Square } from "chess.js";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { Chessboard } from "react-chessboard";
import { api, ApiError } from "@/lib/api";
import type { AiGameState, AiLevel, GameFeedback } from "@/types";

const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export function PlayPage() {
  const [levels, setLevels] = useState<AiLevel[]>([]);
  const [level, setLevel] = useState("intermediate");
  const [playAs, setPlayAs] = useState<"white" | "black">("white");

  const [game, setGame] = useState<AiGameState | null>(null);
  const [fen, setFen] = useState(START_FEN);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [feedback, setFeedback] = useState<GameFeedback | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  useEffect(() => {
    api.aiLevels().then(setLevels).catch(() => setLevels([]));
  }, []);

  const start = () => {
    setError(null);
    setFeedback(null);
    setThinking(true);
    api
      .newAiGame(level, playAs)
      .then((g) => {
        setGame(g);
        setFen(g.fen);
      })
      .catch((e: ApiError) =>
        setError(
          e.status === 503
            ? "Engine offline — Stockfish must be running on the backend to play."
            : e.message
        )
      )
      .finally(() => setThinking(false));
  };

  const onDrop = useCallback(
    (from: Square, to: Square): boolean => {
      if (!game || !game.your_turn || thinking) return false;

      // Validate locally first so illegal drags snap back with no round trip.
      const local = new Chess(fen);
      let uci: string;
      try {
        const m = local.move({ from, to, promotion: "q" });
        if (!m) return false;
        uci = `${m.from}${m.to}${m.promotion ?? ""}`;
      } catch {
        return false;
      }

      setFen(local.fen()); // optimistic: show the player's move immediately
      setThinking(true);
      api
        .playAiMove(game.game_id, uci)
        .then((g) => {
          setGame(g);
          setFen(g.fen);
        })
        .catch((e: ApiError) => {
          setFen(fen); // revert on rejection
          setError(e.message);
        })
        .finally(() => setThinking(false));
      return true;
    },
    [game, fen, thinking]
  );

  const getFeedback = () => {
    if (!game) return;
    setFeedbackLoading(true);
    api
      .aiGameFeedback(game.game_id)
      .then(setFeedback)
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setFeedbackLoading(false));
  };

  const over = game && game.status !== "in_progress";
  const activeLevel = levels.find((l) => l.key === level);

  // Setup screen.
  if (!game) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="mb-2 text-2xl font-extrabold">Play the AI</h1>
        <p className="mb-6 text-sm text-slate-400">
          Play a full game against Stockfish limited to a human-like strength — then
          get coached on how you played.
        </p>

        <div className="space-y-4">
          <div className="card p-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Difficulty
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {levels.map((l) => (
                <button
                  key={l.key}
                  onClick={() => setLevel(l.key)}
                  className={`rounded-xl border p-3 text-left transition ${
                    level === l.key
                      ? "border-brand-500 bg-brand-500/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-100">{l.label}</span>
                    <span className="text-xs text-slate-400">~{l.elo}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{l.blurb}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="card flex items-center justify-between p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Play as
            </p>
            <div className="flex gap-2">
              {(["white", "black"] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setPlayAs(c)}
                  className={`rounded-lg px-4 py-2 text-sm font-semibold capitalize ${
                    playAs === c ? "bg-brand-600 text-white" : "bg-white/5 text-slate-300"
                  }`}
                >
                  {c === "white" ? "♔ White" : "♚ Black"}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-orange-300">{error}</p>}
          <button onClick={start} disabled={thinking} className="btn-primary w-full">
            {thinking ? "Starting…" : "Start game"}
          </button>
        </div>
      </div>
    );
  }

  // Game screen.
  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="aspect-square w-full overflow-hidden rounded-2xl shadow-2xl ring-1 ring-white/10">
          <Chessboard
            position={fen}
            onPieceDrop={(s, t) => onDrop(s as Square, t as Square)}
            boardOrientation={game.player_color}
            arePiecesDraggable={game.your_turn && !over}
            customDarkSquareStyle={{ backgroundColor: "#739552" }}
            customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
            customBoardStyle={{ borderRadius: "1rem" }}
            animationDuration={220}
          />
        </div>
        {error && <p className="text-sm text-orange-300">{error}</p>}
      </div>

      <div className="space-y-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-slate-100">
              Vision64 {activeLevel?.label ?? game.level}
            </span>
            <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs text-slate-400">
              you play {game.player_color}
            </span>
          </div>
          <p className="mt-2 text-sm">
            {over ? (
              <span className="font-semibold text-brand-400">
                {game.status === "checkmate" ? "Checkmate" : "Game drawn"} · {game.result}
              </span>
            ) : thinking ? (
              <span className="text-slate-400">AI is thinking…</span>
            ) : game.your_turn ? (
              <span className="text-slate-200">Your move.</span>
            ) : (
              <span className="text-slate-400">Waiting…</span>
            )}
          </p>
        </div>

        <AnimatePresence>
          {over && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              {feedback ? (
                <div className="card p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Coach's report
                  </p>
                  <p className="text-sm text-slate-100">{feedback.summary}</p>
                  <p className="mt-2 text-2xl font-extrabold text-brand-400">
                    {feedback.accuracy}%
                  </p>
                  {Object.keys(feedback.weakness_tags).length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {Object.entries(feedback.weakness_tags).map(([tag, n]) => (
                        <span
                          key={tag}
                          className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-400"
                        >
                          {tag.replace(/_/g, " ")} ×{n}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={getFeedback}
                  disabled={feedbackLoading}
                  className="btn-primary w-full"
                >
                  {feedbackLoading ? "Analysing your game…" : "📊 Get coaching feedback"}
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="card">
          <div className="border-b border-white/10 px-4 py-2 text-sm font-bold uppercase tracking-wide text-slate-300">
            Moves
          </div>
          <div className="max-h-64 overflow-y-auto p-3 font-mono text-sm text-slate-200">
            {game.moves_san.length === 0 ? (
              <span className="text-slate-500">No moves yet.</span>
            ) : (
              game.moves_san.map((san, i) => (
                <span key={i} className="mr-2">
                  {i % 2 === 0 && <span className="text-slate-500">{i / 2 + 1}.</span>} {san}
                </span>
              ))
            )}
          </div>
        </div>

        <button onClick={() => setGame(null)} className="btn-ghost w-full">
          New game
        </button>
      </div>
    </div>
  );
}
