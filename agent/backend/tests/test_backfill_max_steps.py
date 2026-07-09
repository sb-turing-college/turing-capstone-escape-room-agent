"""Tests for legacy max_steps inference helpers."""

from __future__ import annotations

from agent.run_max_steps_infer import infer_max_steps_from_step_contents, infer_max_steps_from_steps


def test_infer_from_last_observation_json():
    contents = [
        '{"room": "library", "commands_used": 1, "commands_remaining": 11}',
        '{"room": "parlor", "commands_used": 12, "commands_remaining": 0}',
    ]
    assert infer_max_steps_from_step_contents(contents) == 12


def test_infer_from_continue_start_nudge_when_no_observation_budget():
    steps = [
        {
            "type": "system",
            "content": (
                "Run status: commands_used=0/12, human_assists_remaining=2 — "
                "fresh segment budget."
            ),
        }
    ]
    assert infer_max_steps_from_steps(steps) == 12


def test_infer_from_low_budget_system_line():
    steps = [
        {
            "type": "system",
            "content": "Low send_command budget — nudging ask_human (2/12 remaining)",
        }
    ]
    assert infer_max_steps_from_steps(steps) == 12


def test_returns_none_when_no_signals():
    assert infer_max_steps_from_step_contents(["plain text", '{"room": "library"}']) is None
