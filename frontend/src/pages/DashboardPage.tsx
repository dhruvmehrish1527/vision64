// Player dashboard: headline stats + a chart of the most common mistake
// patterns detected across analysed games.

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import type { AccuracyPoint, Dashboard } from "@/types";

/** Compares the recent half of the trend with the earlier half. */
function TrendDelta({ trend }: { trend: AccuracyPoint[] }) {
  const mid = Math.floor(trend.length / 2);
  const avg = (xs: AccuracyPoint[]) =>
    xs.reduce((s, p) => s + p.accuracy, 0) / (xs.length || 1);
  const delta = avg(trend.slice(mid)) - avg(trend.slice(0, mid));
  const up = delta >= 0;
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-bold ${
        up ? "bg-emerald-500/15 text-emerald-300" : "bg-orange-500/15 text-orange-300"
      }`}
      title="Recent games vs. earlier games"
    >
      {up ? "▲" : "▼"} {Math.abs(delta).toFixed(1)} pts
    </span>
  );
}

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-extrabold text-slate-50">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [trend, setTrend] = useState<AccuracyPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((e: ApiError) => setError(e.message));
    api.accuracyTrend().then(setTrend).catch(() => setTrend([]));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-center text-orange-300">
        Could not load dashboard: {error}
      </div>
    );
  }
  if (!data) {
    return <div className="mx-auto max-w-3xl px-4 py-10 text-center text-slate-500">Loading…</div>;
  }

  const weaknessData = data.top_weaknesses.map((w) => ({
    name: w.pattern.replace(/_/g, " "),
    count: w.count,
  }));

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <h1 className="text-2xl font-extrabold">Your progress</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatTile label="Rating" value={String(data.rating)} />
        <StatTile label="Puzzle rating" value={String(data.puzzle_rating)} />
        <StatTile label="Games analyzed" value={String(data.games_analyzed)} />
        <StatTile
          label="Avg accuracy"
          value={data.average_accuracy !== null ? `${data.average_accuracy}%` : "—"}
        />
        <StatTile
          label="Puzzle accuracy"
          value={data.puzzle_accuracy !== null ? `${data.puzzle_accuracy}%` : "—"}
        />
        <StatTile label="Streak" value={`${data.streak_days}d`} sub={`${data.training_minutes} min trained`} />
      </div>

      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wide text-slate-300">
            Accuracy over time
          </h2>
          {trend.length > 1 && <TrendDelta trend={trend} />}
        </div>
        {trend.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Review a few games and your accuracy trend will appear here.
          </p>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend.map((p, i) => ({ ...p, n: i + 1 }))}>
                <defs>
                  <linearGradient id="accFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                <XAxis dataKey="n" stroke="#94a3b8" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} width={32} />
                {/* 80% is a useful "solid club play" reference line. */}
                <ReferenceLine y={80} stroke="#ffffff25" strokeDasharray="4 4" />
                <Tooltip
                  contentStyle={{
                    background: "#111827",
                    border: "1px solid #ffffff20",
                    borderRadius: 12,
                  }}
                  formatter={(v: number) => [`${v}%`, "accuracy"]}
                  labelFormatter={(l) => `Game ${l}`}
                />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#22c55e"
                  strokeWidth={2}
                  fill="url(#accFill)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <a
        href="/training"
        className="card flex items-center justify-between p-5 transition hover:bg-white/5"
      >
        <div>
          <p className="text-sm font-bold text-slate-100">Your training plan</p>
          <p className="mt-0.5 text-xs text-slate-400">
            A weekly plan built from the mistakes found in your games.
          </p>
        </div>
        <span className="text-brand-400">Open →</span>
      </a>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-300">
          Most common mistakes
        </h2>
        {weaknessData.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Import and review a few games to reveal your recurring patterns — Vision64
            will then build a training plan around them.
          </p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weaknessData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="#94a3b8"
                  fontSize={12}
                  width={120}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111827",
                    border: "1px solid #ffffff20",
                    borderRadius: 12,
                  }}
                />
                <Bar dataKey="count" fill="#22c55e" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
