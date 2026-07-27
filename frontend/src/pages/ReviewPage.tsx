// Full game review.
//
// Paste a PGN → the backend replays it through Stockfish, classifies every move,
// and returns per-side accuracy, an evaluation timeline, turning points, a
// phase-by-phase breakdown, and the weakness tally. Click any move to see the
// board there and stream a coaching explanation of it. One click also mines the
// game's blunders into personalized puzzles.

import { useMemo, useState } from "react";
import { Chessboard } from "react-chessboard";
import type { Square } from "chess.js";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CoachPanel } from "@/components/CoachPanel";
import { MoveList } from "@/components/MoveList";
import { api, ApiError, coachStream } from "@/lib/api";
import { classificationStyle } from "@/lib/classification";
import type { Classification, GameReview, ReviewedMove } from "@/types";

const SAMPLE_PGN =
  '[White "You"]\n[Black "Opponent"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7 Kxf7 7. Qf3+ Ke6 8. Nc3 Ncb4 9. a3 Nxc2+ 10. Kd1 Nxa1 11. Nxd5 *';

function evalToPlot(m: ReviewedMove): number {
  if (m.mate_in !== null) return m.mate_in > 0 ? 10 : -10;
  const cp = m.eval_cp ?? 0;
  return Math.max(-10, Math.min(10, cp / 100));
}

export function ReviewPage() {
  const [pgn, setPgn] = useState("");
  const [review, setReview] = useState<GameReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPly, setSelectedPly] = useState<number | null>(null);

  const [coachLoading, setCoachLoading] = useState(false);
  const [coachText, setCoachText] = useState<string | null>(null);
  const [coachError, setCoachError] = useState<string | null>(null);
  const [puzzlesMade, setPuzzlesMade] = useState<number | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const runReview = () => {
    setLoading(true);
    setError(null);
    setReview(null);
    setSelectedPly(null);
    setPuzzlesMade(null);
    api
      .importGame(pgn.trim() || SAMPLE_PGN, 12)
      .then((r) => {
        setReview(r);
        if (r.moves.length) selectMove(r.moves[r.moves.length - 1]);
      })
      .catch((e: ApiError) =>
        setError(
          e.status === 503
            ? "Engine offline — Stockfish must be running on the backend to review games."
            : e.message
        )
      )
      .finally(() => setLoading(false));
  };

  const selectMove = (m: ReviewedMove) => {
    setSelectedPly(m.ply);
    if (!m.fen_before) return;
    setCoachLoading(true);
    setCoachText("");
    setCoachError(null);
    coachStream
      .move(m.fen_before, m.uci, 1200, {
        onMeta: () => setCoachLoading(false),
        onText: (chunk) => {
          setCoachLoading(false);
          setCoachText((prev) => (prev ?? "") + chunk);
        },
        onError: (msg) => setCoachError(msg),
      })
      .catch((e: ApiError) => setCoachError(e.message))
      .finally(() => setCoachLoading(false));
  };

  const share = () => {
    if (!review) return;
    api
      .shareGame(review.game.id)
      .then((r) => {
        const url = `${window.location.origin}${r.url_path}`;
        setShareUrl(url);
        // Best-effort clipboard copy; the link is shown either way.
        navigator.clipboard?.writeText(url).then(
          () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          },
          () => undefined
        );
      })
      .catch(() => setShareUrl(null));
  };

  const genPuzzles = () => {
    if (!review) return;
    api
      .generatePuzzlesFromGame(review.game.id)
      .then((r) => setPuzzlesMade(r.created))
      .catch(() => setPuzzlesMade(0));
  };

  const selectedMove = review?.moves.find((m) => m.ply === selectedPly) ?? null;
  const selectedClassification: Classification | null = selectedMove
    ? {
        classification: selectedMove.classification,
        centipawn_loss: selectedMove.centipawn_loss,
        tags: selectedMove.tags,
      }
    : null;

  const classifications = useMemo(() => {
    const map: Record<number, Classification> = {};
    review?.moves.forEach((m) => {
      map[m.ply] = { classification: m.classification, centipawn_loss: m.centipawn_loss, tags: m.tags };
    });
    return map;
  }, [review]);

  const chartData = useMemo(
    () => review?.moves.map((m) => ({ ply: m.ply, eval: evalToPlot(m), san: m.san })) ?? [],
    [review]
  );

  const history = useMemo(
    () =>
      review?.moves.map((m) => ({
        san: m.san,
        uci: m.uci,
        fenBefore: m.fen_before ?? "",
        fenAfter: m.fen_before ?? "",
        color: (m.color === "white" ? "w" : "b") as "w" | "b",
        ply: m.ply,
      })) ?? [],
    [review]
  );

  // Input screen.
  if (!review) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="mb-2 text-2xl font-extrabold">Game Review</h1>
        <p className="mb-4 text-sm text-slate-400">
          Paste a PGN and Vision64 will grade every move, chart the evaluation, find the
          turning points, and coach you through the critical moments.
        </p>
        <textarea
          value={pgn}
          onChange={(e) => setPgn(e.target.value)}
          rows={8}
          placeholder={SAMPLE_PGN}
          className="w-full rounded-xl border border-white/10 bg-ink-900 p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
        />
        {error && <p className="mt-2 text-sm text-orange-300">{error}</p>}
        <div className="mt-3 flex items-center gap-3">
          <button onClick={runReview} disabled={loading} className="btn-primary">
            {loading ? "Reviewing…" : "Review game"}
          </button>
          <button onClick={() => setPgn(SAMPLE_PGN)} className="btn-ghost">
            Use sample game
          </button>
        </div>
        {loading && (
          <p className="mt-4 text-sm text-slate-500">
            Analysing every position with Stockfish… this can take a few seconds.
          </p>
        )}
      </div>
    );
  }

  // Results screen.
  const boardFen = selectedMove?.fen_before ?? review.moves[0]?.fen_before ?? undefined;
  const arrow: [Square, Square, string][] =
    selectedMove && selectedMove.uci.length >= 4
      ? [[selectedMove.uci.slice(0, 2) as Square, selectedMove.uci.slice(2, 4) as Square, "#eab308"]]
      : [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      {/* Header stats */}
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-extrabold">Game Review</h1>
        <div className="flex gap-3">
          <AccuracyPill label="White" value={review.accuracy_white} />
          <AccuracyPill label="Black" value={review.accuracy_black} />
        </div>
        <div className="ml-auto flex gap-2">
          <button onClick={share} className="btn-ghost">
            🔗 Share
          </button>
          <button onClick={genPuzzles} className="btn-ghost">
            🧩 Make puzzles from this game
          </button>
          <button onClick={() => setReview(null)} className="btn-ghost">
            New review
          </button>
        </div>
      </div>
      {shareUrl && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-500/30 bg-brand-500/10 px-4 py-2 text-sm">
          <span className="text-brand-300">
            {copied ? "Link copied!" : "Anyone with this link can view the game:"}
          </span>
          <code className="truncate rounded bg-ink-900 px-2 py-1 text-xs text-slate-300">
            {shareUrl}
          </code>
        </div>
      )}
      {puzzlesMade !== null && (
        <p className="text-sm text-brand-400">
          Created {puzzlesMade} puzzle{puzzlesMade === 1 ? "" : "s"} from your mistakes — try
          them in the Puzzles tab.
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
        {/* Left: board + coach */}
        <div className="space-y-4">
          <div className="aspect-square w-full overflow-hidden rounded-2xl shadow-2xl ring-1 ring-white/10">
            {boardFen && (
              <Chessboard
                position={boardFen}
                arePiecesDraggable={false}
                boardOrientation="white"
                customArrows={arrow}
                customDarkSquareStyle={{ backgroundColor: "#739552" }}
                customLightSquareStyle={{ backgroundColor: "#ebecd0" }}
                customBoardStyle={{ borderRadius: "1rem" }}
              />
            )}
          </div>
          <CoachPanel
            loading={coachLoading}
            classification={selectedClassification}
            explanation={coachText}
            error={coachError}
          />
        </div>

        {/* Right: eval graph + move list */}
        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-300">
              Evaluation timeline
            </h2>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  onClick={(s: { activeLabel?: string | number }) => {
                    const ply = Number(s?.activeLabel);
                    const m = review.moves.find((mm) => mm.ply === ply);
                    if (m) selectMove(m);
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis dataKey="ply" stroke="#94a3b8" fontSize={11} />
                  <YAxis domain={[-10, 10]} stroke="#94a3b8" fontSize={11} width={28} />
                  <ReferenceLine y={0} stroke="#ffffff30" />
                  {selectedPly !== null && <ReferenceLine x={selectedPly} stroke="#22c55e" />}
                  <Tooltip
                    contentStyle={{ background: "#111827", border: "1px solid #ffffff20", borderRadius: 12 }}
                    formatter={(v: number) => [`${v > 0 ? "+" : ""}${v.toFixed(1)}`, "eval"]}
                    labelFormatter={(l) => `Move ${l}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="eval"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {review.biggest_mistake_ply && (
              <InsightCard title="Biggest mistake">
                <button
                  onClick={() => {
                    const m = review.moves.find((mm) => mm.ply === review.biggest_mistake_ply);
                    if (m) selectMove(m);
                  }}
                  className="text-sm font-semibold text-red-300 hover:underline"
                >
                  Move {Math.ceil(review.biggest_mistake_ply / 2)} — click to review
                </button>
              </InsightCard>
            )}
            <InsightCard title="Turning points">
              <p className="text-sm text-slate-300">
                {review.turning_points.length
                  ? review.turning_points.map((p) => Math.ceil(p / 2)).join(", ")
                  : "None — a steady game."}
              </p>
            </InsightCard>
          </div>

          <PhaseBreakdown phases={review.phases} />

          <div className="card">
            <div className="border-b border-white/10 px-4 py-2 text-sm font-bold uppercase tracking-wide text-slate-300">
              Moves — click any to coach
            </div>
            <MoveList
              history={history}
              cursor={history.findIndex((h) => h.ply === selectedPly)}
              classifications={classifications}
              onSelect={(idx) => {
                const m = review.moves[idx];
                if (m) selectMove(m);
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function AccuracyPill({ label, value }: { label: string; value: number }) {
  const color = value >= 90 ? "text-emerald-300" : value >= 75 ? "text-brand-400" : "text-orange-300";
  return (
    <div className="rounded-xl bg-white/5 px-3 py-1.5">
      <span className="text-xs text-slate-400">{label} accuracy </span>
      <span className={`text-sm font-bold ${color}`}>{value}%</span>
    </div>
  );
}

function InsightCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
      {children}
    </div>
  );
}

function PhaseBreakdown({ phases }: { phases: GameReview["phases"] }) {
  const order = ["opening", "middlegame", "endgame"];
  const present = order.filter((k) => phases[k]);
  if (!present.length) return null;
  return (
    <div className="card p-4">
      <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-300">
        Phase breakdown
      </h2>
      <div className="grid grid-cols-3 gap-3">
        {present.map((k) => {
          const p = phases[k];
          const topLabel = Object.entries(p.labels).sort((a, b) => b[1] - a[1])[0];
          const style = topLabel ? classificationStyle(topLabel[0] as never) : null;
          return (
            <div key={k} className="rounded-xl bg-white/5 p-3">
              <p className="text-sm font-bold capitalize text-slate-200">{k}</p>
              <p className="mt-1 text-xs text-slate-400">avg loss {p.avg_cp_loss}cp</p>
              {style && topLabel && (
                <p className={`mt-1 text-xs ${style.color}`}>
                  mostly {topLabel[0]}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
