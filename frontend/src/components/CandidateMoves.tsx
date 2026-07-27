// Engine's top-N candidate moves with their evaluations — the "which moves are
// strongest here" view.

import type { Candidate } from "@/types";
import { formatEval } from "@/lib/classification";

interface Props {
  candidates: Candidate[];
  depth: number | null;
  onHover?: (uci: string | null) => void;
}

export function CandidateMoves({ candidates, depth, onHover }: Props) {
  return (
    <div className="card p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-300">
          Top Moves
        </h2>
        {depth !== null && (
          <span className="text-xs text-slate-500">depth {depth}</span>
        )}
      </div>
      {candidates.length === 0 ? (
        <p className="text-sm text-slate-500">Analysing…</p>
      ) : (
        <ol className="space-y-1">
          {candidates.map((c, i) => {
            const good = (c.eval_cp ?? 0) >= 0 || (c.mate_in ?? 0) > 0;
            return (
              <li
                key={c.move_uci}
                onMouseEnter={() => onHover?.(c.move_uci)}
                onMouseLeave={() => onHover?.(null)}
                className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-white/5"
              >
                <span className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{i + 1}</span>
                  <span className="font-mono text-sm font-semibold text-slate-100">
                    {c.move_san}
                  </span>
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 font-mono text-xs font-bold ${
                    good ? "text-emerald-300" : "text-red-300"
                  }`}
                >
                  {formatEval(c.eval_cp, c.mate_in)}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
