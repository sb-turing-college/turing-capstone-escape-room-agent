"""Tests for continue-run command lineage totals."""

from __future__ import annotations

from agent.run_commands import (
    command_lineage_run_ids,
    cumulative_command_count,
    lineage_run_ids,
)


def test_lineage_run_ids_root_to_current():
    continued_from = {
        "run-c": "run-b",
        "run-b": "run-a",
        "run-a": None,
    }
    assert lineage_run_ids("run-c", continued_from) == ["run-a", "run-b", "run-c"]


def test_cumulative_command_count_sums_continue_segments():
    continued_from = {
        "run-c": "run-b",
        "run-b": "run-a",
        "run-a": None,
    }
    segment_counts = {"run-a": 12, "run-b": 5, "run-c": 3}
    is_fresh = {"run-a": False, "run-b": False, "run-c": False}
    assert cumulative_command_count("run-c", segment_counts, continued_from, is_fresh) == 20
    assert cumulative_command_count("run-b", segment_counts, continued_from, is_fresh) == 17
    assert cumulative_command_count("run-a", segment_counts, continued_from, is_fresh) == 12


def test_command_lineage_stops_at_fresh_attempt():
    continued_from = {
        "run-d": "run-c",
        "run-c": "run-b",
        "run-b": "run-a",
        "run-a": None,
    }
    is_fresh = {
        "run-a": False,
        "run-b": True,
        "run-c": False,
        "run-d": False,
    }
    assert command_lineage_run_ids("run-b", continued_from, is_fresh) == ["run-b"]
    assert command_lineage_run_ids("run-c", continued_from, is_fresh) == ["run-b", "run-c"]
    assert command_lineage_run_ids("run-d", continued_from, is_fresh) == ["run-b", "run-c", "run-d"]

    segment_counts = {"run-a": 30, "run-b": 5, "run-c": 10, "run-d": 3}
    assert cumulative_command_count("run-b", segment_counts, continued_from, is_fresh) == 5
    assert cumulative_command_count("run-c", segment_counts, continued_from, is_fresh) == 15
    assert cumulative_command_count("run-d", segment_counts, continued_from, is_fresh) == 18
