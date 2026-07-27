// Visual language for move classifications — one source of truth for the badge
// color, glyph, and label used across the board and move list.

import type { MoveClassification } from "@/types";

interface Style {
  label: string;
  glyph: string;
  color: string; // tailwind text/border color
  bg: string;
}

export const CLASSIFICATION_STYLES: Record<MoveClassification, Style> = {
  Brilliant: { label: "Brilliant", glyph: "!!", color: "text-cyan-300", bg: "bg-cyan-500/15" },
  Great: { label: "Great", glyph: "!", color: "text-blue-300", bg: "bg-blue-500/15" },
  Excellent: { label: "Excellent", glyph: "★", color: "text-emerald-300", bg: "bg-emerald-500/15" },
  Good: { label: "Good", glyph: "✓", color: "text-green-300", bg: "bg-green-500/10" },
  Book: { label: "Book", glyph: "📖", color: "text-amber-200", bg: "bg-amber-500/10" },
  Interesting: { label: "Interesting", glyph: "?!", color: "text-purple-300", bg: "bg-purple-500/15" },
  Inaccuracy: { label: "Inaccuracy", glyph: "?!", color: "text-yellow-300", bg: "bg-yellow-500/15" },
  Mistake: { label: "Mistake", glyph: "?", color: "text-orange-300", bg: "bg-orange-500/15" },
  Blunder: { label: "Blunder", glyph: "??", color: "text-red-400", bg: "bg-red-500/15" },
};

export function classificationStyle(c: MoveClassification): Style {
  return CLASSIFICATION_STYLES[c] ?? CLASSIFICATION_STYLES.Good;
}

// Turn a White-perspective centipawn eval into a compact display string.
export function formatEval(evalCp: number | null, mateIn: number | null): string {
  if (mateIn !== null) return `M${Math.abs(mateIn)}`;
  if (evalCp === null) return "–";
  const pawns = evalCp / 100;
  return `${pawns >= 0 ? "+" : ""}${pawns.toFixed(1)}`;
}
