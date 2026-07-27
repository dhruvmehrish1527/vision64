"""Unit tests for adaptive training plan generation (pure functions)."""

from __future__ import annotations

from app.services.training import CURRICULUM, build_plan, puzzle_theme_for_goal


def test_empty_profile_falls_back_to_fundamentals():
    plan = build_plan({})
    assert len(plan) == 4
    assert plan[0].week_number == 1
    assert "Opening principles" in plan[0].focus_topics


def test_plan_is_ordered_by_impact():
    # The user hangs pieces far more often than they miss forks.
    plan = build_plan({"missed_fork": 3, "hanging_piece": 20})
    assert plan[0].goal == CURRICULUM["hanging_piece"]["goal"]
    assert plan[1].goal == CURRICULUM["missed_fork"]["goal"]


def test_plan_tops_up_to_requested_length():
    plan = build_plan({"hanging_piece": 5}, weeks=4)
    assert len(plan) == 4
    # Weeks are contiguously numbered from 1.
    assert [w.week_number for w in plan] == [1, 2, 3, 4]


def test_unknown_tags_are_ignored():
    plan = build_plan({"not_a_real_pattern": 99})
    # Falls back to fundamentals rather than inventing a week.
    assert plan[0].focus_topics == ["Opening principles", "Control the centre", "Develop and castle early"]


def test_zero_count_patterns_are_skipped():
    plan = build_plan({"hanging_piece": 0})
    assert plan[0].goal != CURRICULUM["hanging_piece"]["goal"]


def test_goal_maps_back_to_puzzle_theme():
    assert puzzle_theme_for_goal(CURRICULUM["missed_fork"]["goal"]) == "fork"
    assert puzzle_theme_for_goal("nonexistent goal") is None
