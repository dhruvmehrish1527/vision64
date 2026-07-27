// A vertical evaluation bar. White's advantage fills from the bottom; the
// height animates smoothly as the evaluation changes.

import { motion } from "framer-motion";
import { formatEval } from "@/lib/classification";

interface Props {
  evalCp: number | null;
  mateIn: number | null;
  orientation: "white" | "black";
}

// Squash centipawns into a 0–100% fill using a gentle curve so huge evals don't
// peg the bar instantly but a decisive edge still reads as near-full.
function fillPercent(evalCp: number | null, mateIn: number | null): number {
  if (mateIn !== null) return mateIn > 0 ? 100 : 0;
  if (evalCp === null) return 50;
  const clamped = Math.max(-1000, Math.min(1000, evalCp));
  return 50 + 50 * (2 / (1 + Math.exp(-0.0025 * clamped)) - 1);
}

export function EvalBar({ evalCp, mateIn, orientation }: Props) {
  const whitePct = fillPercent(evalCp, mateIn);
  const whiteOnBottom = orientation === "white";
  const label = formatEval(evalCp, mateIn);
  const whiteWinning = (evalCp ?? 0) >= 0 || (mateIn ?? 0) > 0;

  return (
    <div
      className="relative h-full w-6 overflow-hidden rounded-lg bg-ink-700 md:w-7"
      title={`Evaluation: ${label}`}
      aria-label={`Evaluation ${label}`}
    >
      <motion.div
        className="absolute inset-x-0 bg-slate-100"
        style={whiteOnBottom ? { bottom: 0 } : { top: 0 }}
        animate={{ height: `${whitePct}%` }}
        transition={{ type: "spring", stiffness: 120, damping: 20 }}
      />
      <span
        className={`absolute inset-x-0 text-center text-[10px] font-bold tabular-nums ${
          whiteWinning ? "text-ink-900" : "text-slate-100"
        } ${whiteOnBottom === whiteWinning ? "bottom-1" : "top-1"}`}
      >
        {label}
      </span>
    </div>
  );
}
