// Modal for importing a game (PGN), a position (FEN), or loading a famous game.

import { motion } from "framer-motion";
import { useState } from "react";

const FAMOUS = [
  {
    name: "Opera Game — Morphy, 1858",
    pgn: '1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0',
  },
  {
    name: "Immortal Game — Anderssen, 1851",
    pgn: "1. e4 e5 2. f4 exf4 3. Bc4 Qh4+ 4. Kf1 b5 5. Bxb5 Nf6 6. Nf3 Qh6 7. d3 Nh5 8. Nh4 Qg5 9. Nf5 c6 10. g4 Nf6 11. Rg1 cxb5 12. h4 Qg6 13. h5 Qg5 14. Qf3 Ng8 15. Bxf4 Qf6 16. Nc3 Bc5 17. Nd5 Qxb2 18. Bd6 Bxg1 19. e5 Qxa1+ 20. Ke2 Na6 21. Nxg7+ Kd8 22. Qf6+ Nxf6 23. Be7# 1-0",
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
  onLoadPgn: (pgn: string) => boolean;
  onLoadFen: (fen: string) => boolean;
}

export function ImportDialog({ open, onClose, onLoadPgn, onLoadFen }: Props) {
  const [tab, setTab] = useState<"pgn" | "fen" | "famous">("pgn");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const submit = () => {
    setError(null);
    const ok = tab === "fen" ? onLoadFen(value.trim()) : onLoadPgn(value.trim());
    if (ok) {
      setValue("");
      onClose();
    } else {
      setError(tab === "fen" ? "That FEN looks invalid." : "Couldn't parse that PGN.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card w-full max-w-lg p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 text-lg font-bold">Import</h2>
        <div className="mb-3 flex gap-1">
          {(["pgn", "fen", "famous"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${
                tab === t ? "bg-brand-600 text-white" : "bg-white/5 text-slate-300"
              }`}
            >
              {t === "famous" ? "Famous games" : t.toUpperCase()}
            </button>
          ))}
        </div>

        {tab === "famous" ? (
          <div className="space-y-2">
            {FAMOUS.map((g) => (
              <button
                key={g.name}
                onClick={() => {
                  onLoadPgn(g.pgn);
                  onClose();
                }}
                className="btn-ghost w-full justify-start"
              >
                {g.name}
              </button>
            ))}
          </div>
        ) : (
          <>
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              rows={tab === "fen" ? 2 : 6}
              placeholder={
                tab === "fen"
                  ? "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                  : "1. e4 e5 2. Nf3 ..."
              }
              className="w-full rounded-xl border border-white/10 bg-ink-900 p-3 font-mono text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
            />
            {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={onClose} className="btn-ghost">
                Cancel
              </button>
              <button onClick={submit} className="btn-primary">
                Load
              </button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}
