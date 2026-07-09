"""Tests for interview chat lineage and summarization helpers."""

from __future__ import annotations

from datetime import datetime

from agent.interview_context import (
    SUMMARY_PREFIX,
    chat_lineage_run_ids,
    context_limit_for_model,
    estimate_tokens,
    load_chat_history,
)
from db.models import ChatMessageRecord, RunRecord


def test_estimate_tokens_and_model_limit():
    assert estimate_tokens("abcd") == 1
    assert context_limit_for_model("google/gemini-2.5-flash") >= 100_000
    assert context_limit_for_model("unknown/vendor-model") == 32_000


def test_chat_lineage_includes_continued_from_runs(db_session):
    root = RunRecord(
        id="run-root",
        explorer_model="test/model",
        memory_model="test/model",
        status="failed",
        memory_session_id="session-a",
    )
    child = RunRecord(
        id="run-child",
        explorer_model="test/model",
        memory_model="test/model",
        status="running",
        continued_from_run_id="run-root",
        memory_session_id="session-a",
    )
    db_session.add(root)
    db_session.add(child)
    db_session.commit()

    db_session.add(
        ChatMessageRecord(
            run_id="run-root",
            role="user",
            content="Why did you go north?",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
        )
    )
    db_session.add(
        ChatMessageRecord(
            run_id="run-child",
            role="assistant",
            content="Because the map showed a parlor exit.",
            timestamp=datetime(2026, 1, 1, 12, 5, 0),
        )
    )
    db_session.commit()

    lineage = chat_lineage_run_ids(db_session, child)
    assert lineage == ["run-root", "run-child"]

    history = load_chat_history(db_session, child)
    assert len(history) == 2
    assert history[0].content.startswith("Why did you go north")
    assert SUMMARY_PREFIX not in history[1].content


def test_chat_lineage_spans_memory_session_across_fresh_attempt(db_session):
    root = RunRecord(
        id="run-root",
        explorer_model="test/model",
        memory_model="test/model",
        status="failed",
        memory_session_id="session-a",
    )
    fresh_child = RunRecord(
        id="run-fresh",
        explorer_model="test/model",
        memory_model="test/model",
        status="completed",
        continued_from_run_id="run-root",
        is_fresh_attempt=True,
        memory_session_id="session-a",
    )
    db_session.add(root)
    db_session.add(fresh_child)
    db_session.add(
        ChatMessageRecord(
            run_id="run-root",
            role="user",
            content="Old attempt question",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
        )
    )
    db_session.add(
        ChatMessageRecord(
            run_id="run-fresh",
            role="user",
            content="New attempt question",
            timestamp=datetime(2026, 1, 1, 13, 0, 0),
        )
    )
    db_session.commit()

    lineage = chat_lineage_run_ids(db_session, fresh_child)
    assert lineage == ["run-root", "run-fresh"]

    history = load_chat_history(db_session, fresh_child)
    assert len(history) == 2
    assert history[0].content == "Old attempt question"
    assert history[1].content == "New attempt question"
