"""Tests for interview transcript lineage and replay filtering."""

from __future__ import annotations

from agent.interview import build_transcript, filter_steps_for_transcript
from db.models import RunRecord, StepRecord


def _step(
    run_id: str,
    step_number: int,
    step_type: str,
    content: str,
    *,
    extra: dict | None = None,
) -> StepRecord:
    return StepRecord(
        run_id=run_id,
        step_number=step_number,
        type=step_type,
        content=content,
        extra=extra,
    )


def test_filter_steps_for_transcript_drops_replayed_flag(db_session):
    run = RunRecord(
        id="run-a",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
    )
    steps = [
        _step("run-a", 1, "room_visited", "The Library", extra={"replayed": True}),
        _step("run-a", 2, "thought", "Need the key"),
    ]
    filtered = filter_steps_for_transcript(steps, run)
    assert [s.type for s in filtered] == ["thought"]


def test_filter_steps_for_transcript_drops_pre_game_update_map_on_continue(db_session):
    run = RunRecord(
        id="run-child",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
        continued_from_run_id="run-root",
    )
    steps = [
        _step("run-child", 1, "memory_retrieved", "Prior summary"),
        _step("run-child", 2, "room_visited", "The Library"),
        _step("run-child", 3, "item_discovered", "brass_key"),
        _step("run-child", 4, "game_update", "You are in the library."),
        _step("run-child", 5, "action", "send_command: read secret_book"),
        _step("run-child", 6, "room_visited", "The Parlor"),
    ]
    filtered = filter_steps_for_transcript(steps, run)
    assert [s.type for s in filtered] == [
        "memory_retrieved",
        "game_update",
        "action",
        "room_visited",
    ]


def test_build_transcript_spans_lineage_and_filters_replay(db_session):
    root = RunRecord(
        id="run-root",
        explorer_model="test/model",
        memory_model="test/model",
        status="failed",
    )
    child = RunRecord(
        id="run-child",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
        continued_from_run_id="run-root",
    )
    db_session.add(root)
    db_session.add(child)
    db_session.add(_step("run-root", 1, "human_hint", "Check the painting"))
    db_session.add(_step("run-root", 2, "action", "send_command: go north"))
    db_session.add(_step("run-child", 1, "room_visited", "The Library", extra={"replayed": True}))
    db_session.add(_step("run-child", 2, "game_update", "Library text"))
    db_session.add(_step("run-child", 3, "human_hint", "Read the secret book"))
    db_session.commit()

    transcript = build_transcript(db_session, child)

    assert "=== Run run-root ===" in transcript
    assert "[human_hint]" in transcript
    assert "Check the painting" in transcript
    assert "=== Run run-child (continued from run-root) ===" in transcript
    assert "Read the secret book" in transcript
    assert "The Library" not in transcript


def test_build_transcript_excludes_parent_after_fresh_attempt(db_session):
    root = RunRecord(
        id="run-root",
        explorer_model="test/model",
        memory_model="test/model",
        status="failed",
    )
    fresh_child = RunRecord(
        id="run-fresh",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
        continued_from_run_id="run-root",
        is_fresh_attempt=True,
    )
    db_session.add(root)
    db_session.add(fresh_child)
    db_session.add(_step("run-root", 1, "action", "send_command: go north"))
    db_session.add(_step("run-fresh", 1, "memory_retrieved", "Prior lesson from memory"))
    db_session.add(_step("run-fresh", 2, "action", "send_command: look"))
    db_session.commit()

    transcript = build_transcript(db_session, fresh_child)

    assert "go north" not in transcript
    assert "=== Run run-root ===" not in transcript
    assert "=== Run run-fresh (new attempt from run-root) ===" in transcript
    assert "[memory_retrieved]" in transcript
    assert "Prior lesson from memory" in transcript
