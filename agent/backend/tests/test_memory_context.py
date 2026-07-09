"""Tests for structured memory retrieval and priority formatting."""

from __future__ import annotations

from typing import Any

from agent.memory_agent import MemoryAgent
from agent.run_memory import compose_run_memory_document, format_state_footer

SESSION_A = "session-a"
SESSION_B = "session-b"


class _FakeChromaStore:
    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self.entries = entries or []

    @property
    def count(self) -> int:
        return len(self.entries)

    def add(self, doc_id: str, document: str, metadata: dict[str, Any]) -> None:
        self.entries.append({"id": doc_id, "document": document, "metadata": metadata})

    def list_entries(self) -> list[dict[str, Any]]:
        return list(self.entries)

    def get_entry(self, doc_id: str) -> dict[str, Any] | None:
        for entry in self.entries:
            if entry["id"] == doc_id:
                return entry
        return None

    def mark_superseded(self, doc_id: str, superseded_by: str) -> bool:
        entry = self.get_entry(doc_id)
        if entry is None:
            return False
        entry["metadata"]["superseded_by"] = superseded_by
        return True

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        ranked = sorted(
            self.entries,
            key=lambda entry: (
                0 if entry["metadata"].get("source") == "interview" else 1,
                entry["metadata"].get("created_at") or "",
            ),
        )
        return [
            {"document": entry["document"], "metadata": entry["metadata"]}
            for entry in ranked[:n_results]
        ]


def test_get_context_structures_interview_and_summaries():
    store = _FakeChromaStore(
        [
            {
                "id": "interview-old",
                "document": "Use speedrun path.",
                "metadata": {
                    "source": "interview",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-01T10:00:00+00:00",
                },
            },
            {
                "id": "interview-new",
                "document": "Do NOT use speedrun path.",
                "metadata": {
                    "source": "interview",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-02T12:00:00+00:00",
                },
            },
            {
                "id": "run-1",
                "document": "Summary says speedrun worked.",
                "metadata": {
                    "source": "run_summary",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-01T11:00:00+00:00",
                },
            },
        ]
    )
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    context, hits = agent.get_context(SESSION_A)

    assert "Player instructions (agent chat" in context
    assert "Past run summaries" in context
    assert context.index("Use speedrun path.") < context.index("Do NOT use speedrun path.")
    assert "Summary says speedrun worked." in context
    assert len(hits) == 3
    assert hits[0]["document"] == "Use speedrun path."


def test_get_context_excludes_superseded_agent_chat_notes():
    store = _FakeChromaStore(
        [
            {
                "id": "interview-old",
                "document": "Old hook-and-rope route.",
                "metadata": {
                    "source": "agent_chat",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-01T10:00:00+00:00",
                    "superseded_by": "interview-new",
                },
            },
            {
                "id": "interview-new",
                "document": "Updated 3-step speedrun.",
                "metadata": {
                    "source": "agent_chat",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-02T12:00:00+00:00",
                },
            },
        ]
    )
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    context, hits = agent.get_context(SESSION_A)

    assert "Old hook-and-rope route." not in context
    assert "Updated 3-step speedrun." in context
    assert len(hits) == 1


def test_get_context_orders_interview_without_timestamps_by_insertion():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    store.add(
        "interview-old",
        "Use speedrun path.",
        {"source": "interview", "memory_session_id": SESSION_A},
    )
    store.add(
        "interview-new",
        "Do NOT use speedrun path.",
        {"source": "interview", "memory_session_id": SESSION_A},
    )

    _context, hits = agent.get_context(SESSION_A)

    assert hits[0]["document"] == "Use speedrun path."


def test_get_context_skips_interview_in_summary_section():
    store = _FakeChromaStore(
        [
            {
                "id": "interview-1",
                "document": "Explore full puzzle chain.",
                "metadata": {
                    "source": "interview",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-02T12:00:00+00:00",
                },
            },
            {
                "id": "run-1",
                "document": "Run summary only.",
                "metadata": {
                    "source": "run_summary",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-01T11:00:00+00:00",
                },
            },
        ]
    )
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    context, hits = agent.get_context(SESSION_A)
    summary_section = context.split("Past run summaries")[1]

    assert "Explore full puzzle chain." not in summary_section
    assert "Run summary only." in summary_section
    assert len(hits) == 2


def test_get_context_fresh_attempt_replaces_state_footer():
    footer = format_state_footer(
        {"room": "parlor", "inventory": [], "ending": None},
        success=False,
        commands_used=12,
        max_commands=20,
    )
    doc = compose_run_memory_document("Memo clues were in the portrait.", footer)
    store = _FakeChromaStore(
        [
            {
                "id": "run-1",
                "document": doc,
                "metadata": {
                    "source": "agent_reflection",
                    "memory_session_id": SESSION_A,
                    "created_at": "2026-01-01T11:00:00+00:00",
                },
            },
        ]
    )
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    context, hits = agent.get_context(SESSION_A, fresh_attempt=True)

    assert "Ground truth (game state at run end):" not in context
    assert "room: parlor" not in context
    assert "Memo clues were in the portrait." in context
    assert "Prior attempt ended at room 'parlor'" in hits[0]["document"]


def test_get_context_isolates_memory_by_session():
    store = _FakeChromaStore(
        [
            {
                "id": "run-a",
                "document": "Session A clue.",
                "metadata": {"source": "run_summary", "memory_session_id": SESSION_A},
            },
            {
                "id": "run-b",
                "document": "Session B clue.",
                "metadata": {"source": "run_summary", "memory_session_id": SESSION_B},
            },
        ]
    )
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    context_a, hits_a = agent.get_context(SESSION_A)
    context_b, hits_b = agent.get_context(SESSION_B)
    empty_context, empty_hits = agent.get_context("brand-new-session")

    assert "Session A clue." in context_a
    assert "Session B clue." not in context_a
    assert len(hits_a) == 1

    assert "Session B clue." in context_b
    assert "Session A clue." not in context_b
    assert len(hits_b) == 1

    assert empty_context == ""
    assert empty_hits == []
