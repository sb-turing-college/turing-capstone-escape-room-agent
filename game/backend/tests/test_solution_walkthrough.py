"""Pytest coverage for the full optimal walkthrough (Chapter 0 → demo ending)."""

from __future__ import annotations

from solution_chain import SOLUTION, run_solution


class TestSolutionWalkthrough:
    def test_full_chain_reaches_demo_ending(self):
        session, last = run_solution()
        assert session.state.flags.is_solved is True
        assert last.ending == "chapter1"
        assert last.room == "parlor"

    def test_solution_has_expected_length(self):
        # Guard against accidental truncation when editing the chain.
        assert len(SOLUTION) == 26
