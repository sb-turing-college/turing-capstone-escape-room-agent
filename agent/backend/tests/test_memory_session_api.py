"""Tests for session-scoped memory helpers and Chroma cleanup."""

from __future__ import annotations

from agent.memory_session import filter_memory_entries
from memory.chroma_store import ChromaStore


def test_filter_memory_entries_scopes_by_session_and_legacy_run_id():
    entries = [
        {
            "id": "a",
            "document": "session A",
            "metadata": {"memory_session_id": "sess-a", "source": "run_summary"},
        },
        {
            "id": "b",
            "document": "session B",
            "metadata": {"memory_session_id": "sess-b", "source": "run_summary"},
        },
        {
            "id": "c",
            "document": "legacy",
            "metadata": {"run_id": "run-old", "source": "run_summary"},
        },
    ]
    filtered = filter_memory_entries(entries, "sess-a", {"run-old"})
    assert [entry["id"] for entry in filtered] == ["a", "c"]


def test_chroma_clear_session_keeps_other_sessions(tmp_path):
    store = ChromaStore(str(tmp_path / "chroma"))
    store.add(
        "entry-a",
        "memory A",
        {"source": "run_summary", "memory_session_id": "sess-a", "run_id": "run-a"},
    )
    store.add(
        "entry-b",
        "memory B",
        {"source": "run_summary", "memory_session_id": "sess-b", "run_id": "run-b"},
    )

    removed = store.clear_session("sess-a", {"run-a"})
    assert removed == 1
    assert store.count == 1
    remaining = store.list_entries()
    assert remaining[0]["metadata"]["memory_session_id"] == "sess-b"
