"""Tests for injected run-loop nudges."""

from __future__ import annotations

from agent.run_nudges import (
    build_continue_start_nudge,
    build_fresh_attempt_nudge,
    build_low_budget_ask_human_nudge,
    build_round_continuation_nudge,
    low_budget_command_threshold,
)


def test_low_budget_threshold_is_quarter_of_max_steps():
    assert low_budget_command_threshold(20) == 5
    assert low_budget_command_threshold(15) == 3
    assert low_budget_command_threshold(3) == 1


def test_build_fresh_attempt_nudge_text():
    nudge = build_fresh_attempt_nudge()
    assert "new attempt" in nudge.lower()
    assert "reset" in nudge.lower()


def test_build_low_budget_ask_human_nudge_text():
    nudge = build_low_budget_ask_human_nudge(5, 2)
    assert "5 send_command(s) remaining" in nudge
    assert "ask_human NOW" in nudge
    assert "2 assist(s) left" in nudge


def test_build_continue_start_nudge_resets_budget():
    nudge = build_continue_start_nudge(max_steps=12, human_assists_remaining=2)
    assert nudge == (
        "Run status: commands_used=0/12, human_assists_remaining=2 — "
        "fresh command budget for this segment."
    )


def test_build_round_continuation_nudge_includes_run_status():
    nudge = build_round_continuation_nudge(
        commands_used=9,
        max_steps=20,
        human_assists_remaining=2,
        ending=None,
        room="library",
        inventory=["brass_key"],
    )
    assert "Run status: commands_used=9/20, human_assists_remaining=2." in nudge
    assert "ask_human if appropriate" in nudge
    assert "Current room: library" in nudge


def test_build_round_continuation_nudge_without_assists():
    nudge = build_round_continuation_nudge(
        commands_used=3,
        max_steps=20,
        human_assists_remaining=0,
        ending=None,
        room="parlor",
        inventory=[],
    )
    assert "human_assists_remaining=0" in nudge
    assert "Continue with send_command." in nudge
    assert "ask_human" not in nudge
