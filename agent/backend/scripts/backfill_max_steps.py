"""Backfill runs.max_steps for legacy rows from observation / nudge step content."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent.run_max_steps_infer import infer_max_steps_from_steps

DB_PATH = BACKEND_ROOT / "agent.db"


def _load_steps(conn: sqlite3.Connection, run_id: str) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT type, content
        FROM steps
        WHERE run_id = ?
        ORDER BY step_number
        """,
        (run_id,),
    ).fetchall()
    return [{"type": row[0], "content": row[1]} for row in rows]


def backfill(conn: sqlite3.Connection, *, dry_run: bool) -> tuple[int, int, int]:
    legacy_runs = conn.execute(
        """
        SELECT id
        FROM runs
        WHERE max_steps IS NULL
        ORDER BY started_at
        """
    ).fetchall()

    updated = 0
    skipped = 0
    for (run_id,) in legacy_runs:
        steps = _load_steps(conn, run_id)
        inferred = infer_max_steps_from_steps(steps)
        if inferred is None:
            skipped += 1
            print(f"skip {run_id}: could not infer max_steps")
            continue
        print(f"{'would set' if dry_run else 'set'} {run_id}: max_steps={inferred}")
        if not dry_run:
            conn.execute(
                "UPDATE runs SET max_steps = ? WHERE id = ?",
                (inferred, run_id),
            )
        updated += 1

    if not dry_run and updated:
        conn.commit()
    return len(legacy_runs), updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill runs.max_steps from legacy step observations."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print inferred values without writing to the database.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help=f"SQLite path (default: {DB_PATH})",
    )
    args = parser.parse_args()

    if not args.db.exists():
        print(f"No database at {args.db}")
        return

    conn = sqlite3.connect(args.db)
    try:
        total, updated, skipped = backfill(conn, dry_run=args.dry_run)
        print(
            f"Done: {total} legacy run(s), "
            f"{updated} {'would update' if args.dry_run else 'updated'}, "
            f"{skipped} skipped"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
