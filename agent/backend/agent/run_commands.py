"""Command counts across continue-run lineages."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from db.models import RunRecord


def lineage_run_ids(run_id: str, continued_from: Mapping[str, str | None]) -> list[str]:
    """Root → current run ids along the full parent chain (inclusive)."""
    chain: list[str] = []
    current: str | None = run_id
    seen: set[str] = set()
    while current and current not in seen:
        chain.append(current)
        seen.add(current)
        current = continued_from.get(current)
    return list(reversed(chain))


def command_lineage_run_ids(
    run_id: str,
    continued_from: Mapping[str, str | None],
    is_fresh_attempt: Mapping[str, bool],
) -> list[str]:
    """Root → current ids for command totals; stops before a fresh-attempt parent."""
    chain: list[str] = [run_id]
    current_id = run_id
    seen: set[str] = {run_id}
    while True:
        if is_fresh_attempt.get(current_id, False):
            break
        parent = continued_from.get(current_id)
        if not parent or parent in seen:
            break
        chain.insert(0, parent)
        seen.add(parent)
        current_id = parent
    return chain


def lineage_run_ids_db(db: Session, run_id: str) -> list[str]:
    """Root → current run ids by walking `continued_from_run_id` in the database."""
    continued_from: dict[str, str | None] = {}
    current: str | None = run_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        row = db.query(RunRecord).filter_by(id=current).one_or_none()
        if row is None:
            break
        continued_from[row.id] = row.continued_from_run_id
        current = row.continued_from_run_id
    return lineage_run_ids(run_id, continued_from)


def command_lineage_run_ids_db(db: Session, run_id: str) -> list[str]:
    """Command-total lineage; fresh attempts reset the cumulative chain."""
    continued_from: dict[str, str | None] = {}
    is_fresh_attempt: dict[str, bool] = {}
    current: str | None = run_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        row = db.query(RunRecord).filter_by(id=current).one_or_none()
        if row is None:
            break
        continued_from[row.id] = row.continued_from_run_id
        is_fresh_attempt[row.id] = bool(row.is_fresh_attempt)
        current = row.continued_from_run_id
    return command_lineage_run_ids(run_id, continued_from, is_fresh_attempt)


def cumulative_command_count(
    run_id: str,
    segment_counts: Mapping[str, int],
    continued_from: Mapping[str, str | None],
    is_fresh_attempt: Mapping[str, bool] | None = None,
) -> int:
    """Sum send_command steps for this run and continue segments back to the last fresh attempt."""
    if is_fresh_attempt is None:
        lineage = lineage_run_ids(run_id, continued_from)
    else:
        lineage = command_lineage_run_ids(run_id, continued_from, is_fresh_attempt)
    return sum(segment_counts.get(rid, 0) for rid in lineage)
