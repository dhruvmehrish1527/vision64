// Opening explorer.
//
// Searchable database of openings with ECO code, win rates, typical plans, the
// mistakes players actually make, and famous practitioners. Selecting one
// replays its moves on a board, and it can be saved to a personal repertoire
// for White or Black.

import { Chess } from "chess.js";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Chessboard } from "react-chessboard";
import { api, ApiError } from "@/lib/api";
import type { Opening, RepertoireItem } from "@/types";

const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export function OpeningsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Opening[]>([]);
  const [selected, setSelected] = useState<Opening | null>(null);
  const [repertoire, setRepertoire] = useState<RepertoireItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  // How many moves of the selected line are shown on the board.
  const [ply, setPly] = useState(0);

  useEffect(() => {
    const id = setTimeout(() => {
      api
        .searchOpenings(query)
        .then((r) => {
          setResults(r);
          setSelected((cur) => cur ?? r[0] ?? null);
        })
        .catch((e: ApiError) => setError(e.message));
    }, 180); // debounce typing
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    api.repertoire().then(setRepertoire).catch(() => setRepertoire([]));
  }, []);

  useEffect(() => {
    if (selected) setPly(selected.moves.length);
  }, [selected]);

  // Replay the selected line up to `ply` to get the board position.
  const fen = useMemo(() => {
    if (!selected) return START_FEN;
    const game = new Chess();
    for (const san of selected.moves.slice(0, ply)) {
      try {
        game.move(san);
      } catch {
        break;
      }
    }
    return game.fen();
  }, [selected, ply]);

  const save = (color: "white" | "black") => {
    if (!selected) return;
    api
      .saveOpening(selected.eco, color)
      .then((item) =>
        setRepertoire((prev) =>
          prev.some((p) => p.id === item.id) ? prev : [...prev, item]
        )
      )
      .catch((e: ApiError) => setError(e.message));
  };

  const remove = (id: number) => {
    api
      .removeOpening(id)
      .then(() => setRepertoire((prev) => prev.filter((p) => p.id !== id)))
      .catch((e: ApiError) => setError(e.message));
  };

  return (
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[300px_1fr]">
      {/* Left: search + results + repertoire */}
      <div className="space-y-4">
        <div className="card p-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search openings or ECO…"
            className="w-full rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
          />
          <div className="mt-3 max-h-[420px] space-y-1 overflow-y-auto">
            {results.map((o) => (
              <button
                key={o.eco + o.name}
                onClick={() => setSelected(o)}
                className={`w-full rounded-lg px-3 py-2 text-left transition ${
                  selected?.eco === o.eco && selected?.name === o.name
                    ? "bg-brand-600 text-white"
                    : "hover:bg-white/5"
                }`}
              >
                <span className="mr-2 font-mono text-xs opacity-70">{o.eco}</span>
                <span className="text-sm font-semibold">{o.name}</span>
              </button>
            ))}
            {results.length === 0 && (
              <p className="px-2 py-4 text-center text-sm text-slate-500">No matches.</p>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            My repertoire
          </h2>
          {repertoire.length === 0 ? (
            <p className="text-xs text-slate-500">
              Save openings here to build a repertoire for each colour.
            </p>
          ) : (
            <ul className="space-y-1">
              {repertoire.map((r) => (
                <li
                  key={r.id}
                  className="group flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-white/5"
                >
                  <span className="text-xs">
                    <span className="mr-1">{r.color === "white" ? "♔" : "♚"}</span>
                    {r.name}
                  </span>
                  <button
                    onClick={() => remove(r.id)}
                    className="text-xs text-slate-500 opacity-0 transition group-hover:opacity-100 hover:text-red-400"
                    aria-label={`Remove ${r.name}`}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Right: detail */}
      <AnimatePresence mode="wait">
        {selected ? (
          <motion.div
            key={selected.eco + selected.name}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-extrabold">{selected.name}</h1>
                <p className="mt-1 font-mono text-sm text-slate-400">
                  {selected.eco} · {selected.moves.join(" ")}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => save("white")} className="btn-ghost text-xs">
                  ♔ Save for White
                </button>
                <button onClick={() => save("black")} className="btn-ghost text-xs">
                  ♚ Save for Black
                </button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-[minmax(0,340px)_1fr]">
              <div className="space-y-3">
                <div className="aspect-square w-full overflow-hidden rounded-2xl ring-1 ring-white/10">
                  <Chessboard
                    position={fen}
                    arePiecesDraggable={false}
                    customDarkSquareStyle={{ backgroundColor: "#739552" }}
                    customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
                    customBoardStyle={{ borderRadius: "1rem" }}
                    animationDuration={200}
                  />
                </div>
                {/* Step through the opening's moves. */}
                <div className="flex flex-wrap gap-1">
                  <button
                    onClick={() => setPly(0)}
                    className={`rounded px-2 py-1 text-xs ${
                      ply === 0 ? "bg-brand-600 text-white" : "bg-white/5 text-slate-300"
                    }`}
                  >
                    start
                  </button>
                  {selected.moves.map((san, i) => (
                    <button
                      key={i}
                      onClick={() => setPly(i + 1)}
                      className={`rounded px-2 py-1 font-mono text-xs ${
                        ply === i + 1 ? "bg-brand-600 text-white" : "bg-white/5 text-slate-300"
                      }`}
                    >
                      {san}
                    </button>
                  ))}
                </div>
                <WinRateBar
                  white={selected.white_win}
                  draw={selected.draw}
                  black={selected.black_win}
                />
              </div>

              <div className="space-y-4">
                <InfoCard title="Typical plans" items={selected.plans} accent="text-brand-400" />
                <InfoCard
                  title="Common mistakes"
                  items={selected.mistakes}
                  accent="text-orange-300"
                />
                <div className="card p-4">
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
                    Famous players
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {selected.famous.map((f) => (
                      <span
                        key={f}
                        className="rounded-lg bg-white/5 px-2.5 py-1 text-xs text-slate-300"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            {error && <p className="text-sm text-orange-300">{error}</p>}
          </motion.div>
        ) : (
          <p className="text-slate-500">Select an opening to explore it.</p>
        )}
      </AnimatePresence>
    </div>
  );
}

function InfoCard({
  title,
  items,
  accent,
}: {
  title: string;
  items: string[];
  accent: string;
}) {
  return (
    <div className="card p-4">
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">{title}</h3>
      <ul className="space-y-2">
        {items.map((t) => (
          <li key={t} className="flex gap-2 text-sm text-slate-200">
            <span className={accent}>•</span>
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WinRateBar({ white, draw, black }: { white: number; draw: number; black: number }) {
  return (
    <div className="card p-4">
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
        Master results
      </h3>
      <div className="flex h-6 overflow-hidden rounded-lg text-[10px] font-bold">
        <div
          className="flex items-center justify-center bg-slate-100 text-ink-900"
          style={{ width: `${white}%` }}
        >
          {white}%
        </div>
        <div
          className="flex items-center justify-center bg-slate-500 text-white"
          style={{ width: `${draw}%` }}
        >
          {draw}%
        </div>
        <div
          className="flex items-center justify-center bg-ink-700 text-slate-200"
          style={{ width: `${black}%` }}
        >
          {black}%
        </div>
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] text-slate-500">
        <span>White wins</span>
        <span>Draw</span>
        <span>Black wins</span>
      </div>
    </div>
  );
}
