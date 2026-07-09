"""Resolve episodic memory scope for a run / playthrough chain."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from db.models import RunRecord


def resolve_memory_session_id(run: RunRecord) -> str:
    """Return the root memory session id for this run's playthrough."""
    return run.memory_session_id or run.id


def run_ids_for_memory_session(db: Session, memory_session_id: str) -> set[str]:
    """All run ids belonging to the same memory session (incl. continuations)."""
    rows = (
        db.query(RunRecord.id)
        .filter(
            (RunRecord.memory_session_id == memory_session_id)
            | (RunRecord.id == memory_session_id)
        )
        .all()
    )
    return {row[0] for row in rows}


def filter_memory_entries(
    entries: list[dict[str, Any]],
    memory_session_id: str,
    run_ids: set[str],
) -> list[dict[str, Any]]:
    """Keep entries tagged for this session, plus legacy rows keyed by run_id."""
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        metadata = entry.get("metadata") or {}
        if metadata.get("memory_session_id") == memory_session_id:
            filtered.append(entry)
        elif not metadata.get("memory_session_id") and metadata.get("run_id") in run_ids:
            filtered.append(entry)
    return filtered
