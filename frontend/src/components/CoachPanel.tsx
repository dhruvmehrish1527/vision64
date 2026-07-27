// The AI coach panel — the product's centerpiece. Shows the classification of
// the last move (or the position plan) plus Claude's natural-language
// explanation, adapted to the player's rating.

import { AnimatePresence, motion } from "framer-motion";
import type { Classification } from "@/types";
import { classificationStyle } from "@/lib/classification";

interface Props {
  loading: boolean;
  classification: Classification | null;
  explanation: string | null;
  error: string | null;
}

export function CoachPanel({ loading, classification, explanation, error }: Props) {
  const style = classification ? classificationStyle(classification.classification) : null;

  return (
    <div className="card flex flex-col p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-300">
          <span className="text-brand-400">♞</span> AI Coach
        </h2>
        {style && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-bold ${style.bg} ${style.color}`}
          >
            {style.glyph} {style.label}
          </span>
        )}
      </div>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-2"
          >
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-3 animate-pulse rounded bg-white/10"
                style={{ width: `${90 - i * 12}%` }}
              />
            ))}
            <p className="pt-1 text-xs text-slate-500">Thinking about this position…</p>
          </motion.div>
        ) : error ? (
          <motion.p
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-orange-300"
          >
            {error}
          </motion.p>
        ) : explanation ? (
          <motion.p
            key="text"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm leading-relaxed text-slate-100"
          >
            {explanation}
          </motion.p>
        ) : (
          <motion.p key="empty" className="text-sm text-slate-500">
            Make a move, or click <em>Explain this position</em>, and I'll tell you the
            ideas behind it — tuned to your rating.
          </motion.p>
        )}
      </AnimatePresence>

      {classification && classification.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {classification.tags.map((t) => (
            <span
              key={t}
              className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-400"
            >
              {t.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
