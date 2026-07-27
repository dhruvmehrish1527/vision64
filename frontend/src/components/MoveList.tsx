// The move history, paired white/black per row, with the active ply highlighted
// and clickable for jump-to navigation. Classification badges appear when a
// move has been analysed.

import type { HistoryEntry } from "@/hooks/useChessGame";
import type { Classification } from "@/types";
import { classificationStyle } from "@/lib/classification";

interface Props {
  history: HistoryEntry[];
  cursor: number;
  classifications: Record<number, Classification>; // keyed by ply
  onSelect: (cursor: number) => void;
}

export function MoveList({ history, cursor, classifications, onSelect }: Props) {
  // Group half-moves into full-move rows.
  const rows: { number: number; white?: HistoryEntry; black?: HistoryEntry; whiteIdx?: number; blackIdx?: number }[] =
    [];
  history.forEach((entry, idx) => {
    const moveNumber = Math.floor(idx / 2) + 1;
    let row = rows[rows.length - 1];
    if (!row || (entry.color === "w" && row.white)) {
      row = { number: moveNumber };
      rows.push(row);
    }
    if (entry.color === "w") {
      row.white = entry;
      row.whiteIdx = idx;
    } else {
      row.black = entry;
      row.blackIdx = idx;
    }
  });

  const cell = (entry: HistoryEntry | undefined, idx: number | undefined) => {
    if (!entry || idx === undefined) return <span className="px-2 text-slate-600">…</span>;
    const active = idx === cursor;
    const cls = classifications[entry.ply];
    const style = cls ? classificationStyle(cls.classification) : null;
    return (
      <button
        onClick={() => onSelect(idx)}
        className={`group inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-sm transition
          ${active ? "bg-brand-600 text-white" : "text-slate-200 hover:bg-white/10"}`}
      >
        <span>{entry.san}</span>
        {style && <span className={`text-xs ${active ? "text-white" : style.color}`}>{style.glyph}</span>}
      </button>
    );
  };

  if (history.length === 0) {
    return (
      <div className="p-6 text-center text-sm text-slate-500">
        No moves yet. Drag a piece or import a game to begin.
      </div>
    );
  }

  return (
    <div className="max-h-[420px] overflow-y-auto p-2">
      <table className="w-full border-collapse">
        <tbody>
          {rows.map((row) => (
            <tr key={row.number} className="align-middle">
              <td className="w-8 select-none py-0.5 pr-1 text-right font-mono text-xs text-slate-500">
                {row.number}.
              </td>
              <td className="py-0.5">{cell(row.white, row.whiteIdx)}</td>
              <td className="py-0.5">{cell(row.black, row.blackIdx)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
