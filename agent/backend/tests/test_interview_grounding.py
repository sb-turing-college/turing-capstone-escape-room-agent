"""Tests for interview command grounding (selected run send_command index)."""

from __future__ import annotations

from agent.interview import (
    extract_send_commands,
    format_command_index,
    format_memory_index,
)
from agent.memory_agent import MemoryAgent
from db.models import RunRecord, StepRecord
from tests.test_interview_memory import _FakeChromaStore


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


def test_extract_send_commands_for_selected_run_only(db_session):
    root = RunRecord(
        id="run-root",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
    )
    fresh = RunRecord(
        id="run-fresh",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
        continued_from_run_id="run-root",
        is_fresh_attempt=True,
    )
    db_session.add(root)
    db_session.add(fresh)
    db_session.add(_step("run-root", 1, "action", "send_command: go north"))
    db_session.add(_step("run-root", 2, "action", "send_command: take hook"))
    db_session.add(_step("run-fresh", 1, "memory_retrieved", "Prior lesson"))
    db_session.add(_step("run-fresh", 2, "action", "send_command: look"))
    db_session.add(_step("run-fresh", 3, "action", "send_command: take brass key"))
    db_session.commit()

    commands = extract_send_commands(db_session, fresh)

    assert commands == ["look", "take brass key"]


def test_format_command_index_lists_ordered_commands():
    run = RunRecord(
        id="run-abc",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
    )
    index = format_command_index(run, ["look", "take brass key"])

    assert "Selected run id: run-abc" in index
    assert "send_command count: 2" in index
    assert "1. look" in index
    assert "2. take brass key" in index


def test_format_memory_index_lists_active_agent_chat_doc_ids():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]
    agent.store_interview_note(
        run_id="run-1",
        memory_session_id="session-x",
        content="Take memo before entering parlor.",
        reason="Hint from interview.",
    )

    index = format_memory_index(agent, "session-x")

    assert "interview-run-1-" in index
    assert "Take memo before entering parlor." in index
