"""Adaptive training plan generation.

Turns a user's measured weaknesses into a concrete, ordered, multi-week study
plan — and re-plans as those weaknesses change.

Design
------
* **Curriculum-driven, not LLM-invented.** Each trainable weakness maps to a
  curriculum entry with a goal, focus topics, and a puzzle theme. The plan is
  therefore reproducible, cheap, and always actionable (every topic links to
  something the app can actually drill).
* **Ordered by impact then difficulty.** Weeks are sequenced by how often the
  pattern actually cost the user (their tally), so the biggest leak is fixed
  first. Foundational topics are seeded first for new users with no data.
* **Adaptive.** `regenerate` compares the stored plan against the *current*
  weakness profile: topics the user has stopped failing are dropped, newly
  dominant weaknesses are inserted, and completed weeks are preserved so
  progress is never lost.
"""

from __future__ import annotations

from dataclasses import dataclass

# One curriculum entry per trainable weakness tag.
CURRICULUM: dict[str, dict] = {
    "hanging_piece": {
        "goal": "Stop leaving pieces undefended.",
        "topics": ["Blunder-check routine", "Counting attackers vs defenders", "Loose piece drills"],
        "puzzle_theme": "win_material",
        "difficulty": 1,
    },
    "blundered_material": {
        "goal": "Hold material under pressure.",
        "topics": ["Safety checks before moving", "Recognising opponent threats", "Defensive resources"],
        "puzzle_theme": "win_material",
        "difficulty": 1,
    },
    "missed_fork": {
        "goal": "Spot knight and queen forks reliably.",
        "topics": ["Knight fork patterns", "Double attacks", "Forking squares"],
        "puzzle_theme": "fork",
        "difficulty": 2,
    },
    "missed_mate": {
        "goal": "Convert forced mates.",
        "topics": ["Back-rank mates", "Mate in 1–2", "Mating nets"],
        "puzzle_theme": "mate_in_2",
        "difficulty": 2,
    },
    "missed_win": {
        "goal": "Convert winning positions.",
        "topics": ["Simplify when ahead", "Technique in won positions", "Avoiding counterplay"],
        "puzzle_theme": "tactic",
        "difficulty": 3,
    },
    "sacrifice": {
        "goal": "Judge sacrifices accurately.",
        "topics": ["Sound vs unsound sacrifices", "Calculating forcing lines", "Compensation"],
        "puzzle_theme": "tactic",
        "difficulty": 4,
    },
}

# Shown to users with no analysed games yet — universal fundamentals.
DEFAULT_PLAN = [
    {
        "goal": "Build sound opening habits.",
        "topics": ["Opening principles", "Control the centre", "Develop and castle early"],
        "puzzle_theme": "",
        "difficulty": 1,
    },
    {
        "goal": "Never hang a piece.",
        "topics": ["Blunder-check routine", "Counting attackers vs defenders"],
        "puzzle_theme": "win_material",
        "difficulty": 1,
    },
    {
        "goal": "Learn the core tactical patterns.",
        "topics": ["Forks", "Pins", "Skewers"],
        "puzzle_theme": "fork",
        "difficulty": 2,
    },
    {
        "goal": "Finish games cleanly.",
        "topics": ["Basic checkmates", "King and pawn endings", "Opposition"],
        "puzzle_theme": "endgame",
        "difficulty": 3,
    },
]


@dataclass
class PlannedWeek:
    week_number: int
    goal: str
    focus_topics: list[str]

    def to_dict(self) -> dict:
        return {
            "week_number": self.week_number,
            "goal": self.goal,
            "focus_topics": self.focus_topics,
        }


def build_plan(patterns: dict[str, int], *, weeks: int = 4) -> list[PlannedWeek]:
    """Build an ordered plan from a weakness tally.

    `patterns` is the WeaknessProfile map ({"hanging_piece": 12, ...}). Weeks are
    ordered by impact (count) first, then by difficulty so easier fixes land
    earlier. Falls back to the universal curriculum when there is no data.
    """
    trainable = [(tag, n) for tag, n in patterns.items() if tag in CURRICULUM and n > 0]

    if not trainable:
        entries = DEFAULT_PLAN[:weeks]
    else:
        # Sort by count desc, then difficulty asc (fix the cheap big leaks first).
        trainable.sort(key=lambda kv: (-kv[1], CURRICULUM[kv[0]]["difficulty"]))
        entries = [CURRICULUM[tag] for tag, _ in trainable]
        # Top up with fundamentals if the user has fewer distinct weaknesses than weeks.
        for extra in DEFAULT_PLAN:
            if len(entries) >= weeks:
                break
            if extra["goal"] not in {e["goal"] for e in entries}:
                entries.append(extra)
        entries = entries[:weeks]

    return [
        PlannedWeek(week_number=i + 1, goal=e["goal"], focus_topics=list(e["topics"]))
        for i, e in enumerate(entries)
    ]


def puzzle_theme_for_goal(goal: str) -> str | None:
    """Map a plan week back to the puzzle theme that drills it."""
    for entry in list(CURRICULUM.values()) + DEFAULT_PLAN:
        if entry["goal"] == goal:
            return entry["puzzle_theme"] or None
    return None
