// Adaptive training plan.
//
// Shows the multi-week plan Vision64 generated from the player's measured
// weaknesses, with a progress ring, per-week focus topics, one-click completion,
// and a "Re-plan" action that adapts the remaining weeks to current data.
// Each week links straight into the puzzle trainer filtered to its theme.

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import type { TrainingPlan } from "@/types";

export function TrainingPage() {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .trainingPlan()
      .then(setPlan)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  const complete = (weekId: number) => {
    setBusy(true);
    api
      .completeWeek(weekId)
      .then(setPlan)
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setBusy(false));
  };

  const replan = () => {
    setBusy(true);
    api
      .regeneratePlan()
      .then(setPlan)
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setBusy(false));
  };

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-center text-orange-300">{error}</div>
    );
  }
  if (!plan) {
    return <div className="mx-auto max-w-3xl px-4 py-10 text-center text-slate-500">Building your plan…</div>;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold">{plan.title}</h1>
          <p className="mt-1 text-sm text-slate-400">
            Built from the mistakes Vision64 found in your games — and updated as you improve.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <ProgressRing percent={plan.progress_percent} />
          <button onClick={replan} disabled={busy} className="btn-ghost">
            ↻ Re-plan
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {plan.weeks.map((w, i) => (
          <motion.div
            key={w.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`card p-5 ${w.completed ? "opacity-70" : ""}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                      w.completed ? "bg-brand-600 text-white" : "bg-white/10 text-slate-300"
                    }`}
                  >
                    {w.completed ? "✓" : w.week_number}
                  </span>
                  <h2
                    className={`text-base font-bold ${
                      w.completed ? "text-slate-400 line-through" : "text-slate-100"
                    }`}
                  >
                    Week {w.week_number} — {w.goal}
                  </h2>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5 pl-9">
                  {w.focus_topics.map((t) => (
                    <span
                      key={t}
                      className="rounded-lg bg-white/5 px-2.5 py-1 text-xs text-slate-300"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                {w.puzzle_theme && (
                  <button
                    onClick={() => navigate(`/puzzles?theme=${w.puzzle_theme}`)}
                    className="btn-ghost text-xs"
                  >
                    🧩 Drill
                  </button>
                )}
                {!w.completed && (
                  <button
                    onClick={() => complete(w.id)}
                    disabled={busy}
                    className="btn-primary text-xs"
                  >
                    Mark done
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function ProgressRing({ percent }: { percent: number }) {
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <div className="relative h-14 w-14" title={`${percent}% complete`}>
      <svg className="h-14 w-14 -rotate-90" viewBox="0 0 56 56">
        <circle cx="28" cy="28" r={radius} fill="none" stroke="#ffffff18" strokeWidth="5" />
        <motion.circle
          cx="28"
          cy="28"
          r={radius}
          fill="none"
          stroke="#22c55e"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          animate={{ strokeDashoffset: offset }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
        {percent}%
      </span>
    </div>
  );
}
