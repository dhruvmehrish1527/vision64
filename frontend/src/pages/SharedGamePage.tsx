// Public view of a shared game.
//
// Reached via /shared/<token> — no sign-in required, since possession of the
// token is the grant. Read-only: visitors can step through the moves and see the
// accuracy scores, but nothing else about the owner is exposed.

import { Chess } from "chess.js";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Chessboard } from "react-chessboard";
import { api, ApiError } from "@/lib/api";
import type { SharedGame } from "@/types";

export function SharedGamePage() {
  const { token = "" } = useParams();
  const [game, setGame] = useState<SharedGame | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ply, setPly] = useState(0);

  useEffect(() => {
    api
      .viewShared(token)
      .then((g) => {
        setGame(g);
        setPly(g.moves_san.length);
      })
      .catch((e: ApiError) => setError(e.message));
  }, [token]);

  const fen = useMemo(() => {
    if (!game) return undefined;
    const board = new Chess();
    for (const san of game.moves_san.slice(0, ply)) {
      try {
        board.move(san);
      } catch {
        break;
      }
    }
    return board.fen();
  }, [game, ply]);

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-lg font-bold text-slate-200">Link not available</p>
        <p className="mt-2 text-sm text-slate-400">{error}</p>
        <a href="/" className="btn-primary mt-6 inline-flex">
          Go to Vision64
        </a>
      </div>
    );
  }
  if (!game) {
    return <div className="px-4 py-16 text-center text-slate-500">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-8">
      <div className="text-center">
        <h1 className="text-xl font-extrabold">
          {game.white} vs {game.black}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {game.result && game.result !== "*" ? `Result ${game.result} · ` : ""}
          shared by {game.shared_by ?? "a Vision64 player"}
        </p>
        <div className="mt-3 flex justify-center gap-3">
          {game.accuracy_white !== null && (
            <span className="rounded-lg bg-white/5 px-3 py-1 text-xs">
              White <b className="text-brand-400">{game.accuracy_white}%</b>
            </span>
          )}
          {game.accuracy_black !== null && (
            <span className="rounded-lg bg-white/5 px-3 py-1 text-xs">
              Black <b className="text-brand-400">{game.accuracy_black}%</b>
            </span>
          )}
        </div>
      </div>

      <div className="mx-auto aspect-square w-full max-w-md overflow-hidden rounded-2xl ring-1 ring-white/10">
        <Chessboard
          position={fen}
          arePiecesDraggable={false}
          customDarkSquareStyle={{ backgroundColor: "#739552" }}
          customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
          customBoardStyle={{ borderRadius: "1rem" }}
        />
      </div>

      <div className="flex items-center justify-center gap-2">
        <button onClick={() => setPly(0)} className="btn-ghost" disabled={ply === 0}>
          ⏮
        </button>
        <button
          onClick={() => setPly((p) => Math.max(0, p - 1))}
          className="btn-ghost"
          disabled={ply === 0}
        >
          ◀
        </button>
        <span className="min-w-16 text-center font-mono text-sm text-slate-400">
          {ply}/{game.moves_san.length}
        </span>
        <button
          onClick={() => setPly((p) => Math.min(game.moves_san.length, p + 1))}
          className="btn-ghost"
          disabled={ply >= game.moves_san.length}
        >
          ▶
        </button>
        <button
          onClick={() => setPly(game.moves_san.length)}
          className="btn-ghost"
          disabled={ply >= game.moves_san.length}
        >
          ⏭
        </button>
      </div>

      <div className="card p-4 font-mono text-sm leading-relaxed text-slate-300">
        {game.moves_san.map((san, i) => (
          <button
            key={i}
            onClick={() => setPly(i + 1)}
            className={`mr-1 rounded px-1 ${
              ply === i + 1 ? "bg-brand-600 text-white" : "hover:bg-white/10"
            }`}
          >
            {i % 2 === 0 && <span className="text-slate-500">{i / 2 + 1}.</span>} {san}
          </button>
        ))}
      </div>

      <p className="pt-2 text-center text-xs text-slate-500">
        Analysed with <a href="/" className="text-brand-400 hover:underline">Vision64</a> —
        the free AI chess coach.
      </p>
    </div>
  );
}
