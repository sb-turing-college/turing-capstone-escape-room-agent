"""Clear stale error_message values from successful or post-success-bug runs."""

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
        completed = conn.execute(
            """
            UPDATE runs
            SET error_message = NULL
            WHERE status = 'completed' AND success = 1 AND error_message IS NOT NULL
            """
        )
        conn.commit()
        print(f"Cleared error_message on {completed.rowcount} completed successful run(s)")

        legacy = conn.execute(
            """
            UPDATE runs
            SET error_message = NULL
            WHERE error_message LIKE '%message_text%'
            """
        )
        conn.commit()
        print(f"Cleared legacy message_text errors on {legacy.rowcount} run(s)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
