// Community: discover other players, follow them, and see their stats.

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { PublicProfile } from "@/types";

export function PlayersPage() {
  const [players, setPlayers] = useState<PublicProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    api
      .players()
      .then(setPlayers)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  const toggle = (p: PublicProfile) => {
    setBusy(p.id);
    const next = !p.is_following;
    api
      .follow(p.id, next)
      .then(() =>
        setPlayers((prev) =>
          prev.map((x) =>
            x.id === p.id
              ? { ...x, is_following: next, followers: x.followers + (next ? 1 : -1) }
              : x
          )
        )
      )
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setBusy(null));
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-extrabold">Players</h1>
        <p className="mt-1 text-sm text-slate-400">
          Follow other players to keep an eye on their progress.
        </p>
      </div>

      {error && <p className="text-sm text-orange-300">{error}</p>}

      {players.length === 0 ? (
        <div className="card p-8 text-center text-sm text-slate-500">
          No other players yet — invite a friend to sign up and they'll show up here.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {players.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="card flex items-center justify-between p-4"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-100">
                  {p.display_name ?? `Player #${p.id}`}
                </p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {p.rating} rating · {p.games_analyzed} games · {p.followers} follower
                  {p.followers === 1 ? "" : "s"}
                </p>
              </div>
              <button
                onClick={() => toggle(p)}
                disabled={busy === p.id}
                className={p.is_following ? "btn-ghost text-xs" : "btn-primary text-xs"}
              >
                {p.is_following ? "Following" : "Follow"}
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
