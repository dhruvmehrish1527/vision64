import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Analysis" },
  { to: "/play", label: "Play" },
  { to: "/review", label: "Review" },
  { to: "/openings", label: "Openings" },
  { to: "/puzzles", label: "Puzzles" },
  { to: "/training", label: "Training" },
  { to: "/players", label: "Players" },
  { to: "/dashboard", label: "Dashboard" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">♞</span>
          <span className="text-lg font-extrabold tracking-tight">
            Vision<span className="text-brand-400">64</span>
          </span>
          <span className="ml-2 hidden rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 sm:inline">
            AI Coach
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-white/10"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
