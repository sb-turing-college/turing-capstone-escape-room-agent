"""CLI walkthrough for the optimal solution chain (verbose output).

Standalone regression script (not pytest). The same chain is asserted in
`tests/test_solution_walkthrough.py`.

Usage (from `backend/`):
    uv run python test_solution.py
"""

from __future__ import annotations

import sys

from game.engine import GameSession
from solution_chain import SOLUTION


def main() -> None:
    session = GameSession()
    print(f"Session: {session.session_id}")
    print(session.get_state().text)
    print()

    last = session.get_state()
    for i, cmd in enumerate(SOLUTION, 1):
        last = session.execute(cmd)
        status = "SOLVED" if last.is_solved else last.room
        print(f"{i:2}. > {cmd}")
        print(f"    {last.text[:120]}{'...' if len(last.text) > 120 else ''}")
        print(f"    Room: {status} | Inventory: {last.inventory}")
        if last.ending:
            print(f"    Ending: {last.ending}")
        print()

    if session.state.flags.is_solved and last.ending == "chapter1":
        print("OK: full solution chain successful (safe solved + demo ending)!")
        sys.exit(0)

    print("FAIL: expected is_solved and ending=chapter1.")
    sys.exit(1)


if __name__ == "__main__":
    main()
