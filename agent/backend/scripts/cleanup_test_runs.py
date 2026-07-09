"""Remove pytest pollution rows from the local agent run history DB."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "agent.db"


def main() -> None:
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        before = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        conn.execute("DELETE FROM runs WHERE explorer_model = ?", ("test/model",))
        conn.commit()
        deleted = conn.total_changes
        after = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        print(f"Deleted {deleted} test run(s); {before} -> {after} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
