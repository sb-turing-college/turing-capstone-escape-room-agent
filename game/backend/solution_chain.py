"""Canonical optimal walkthrough for Chapter 0 (library → demo ending).

Shared by the CLI script `test_solution.py` and pytest
(`tests/test_solution_walkthrough.py`).
"""

from __future__ import annotations

from game.engine import GameSession

SOLUTION: list[str] = [
    "take brass key",
    "use brass key with door",
    "open door",
    "go south",
    "take memo",
    "read memo",
    "take small key",
    "take rope",
    "take hook",
    "go north",
    "use small key with lockbox",
    "open lockbox",
    "take note",
    "read note",
    "go south",
    "use rope with hook",
    "use grappling hook with grate",
    "go south-west",
    "open painting",
    "use safe 617482",
    "open safe",
    "take book",
    "read book",
    "go north-east",
    "speak fiend",
    "go down",
]


def run_solution(session: GameSession | None = None) -> tuple[GameSession, object]:
    """Execute every command in `SOLUTION`. Returns session and last response."""
    game = session or GameSession()
    last = game.get_state()
    for cmd in SOLUTION:
        last = game.execute(cmd)
    return game, last
