"""Tests for interview memory persistence."""

from __future__ import annotations

from typing import Any

from agent.memory_agent import MemoryAgent


class _FakeChromaStore:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, dict[str, Any]]] = []

    def add(self, doc_id: str, document: str, metadata: dict[str, Any]) -> None:
        self.items.append((doc_id, document, metadata))

    @property
    def count(self) -> int:
        return len(self.items)

    def list_entries(self) -> list[dict[str, Any]]:
        return [
            {"id": doc_id, "document": document, "metadata": metadata}
            for doc_id, document, metadata in self.items
        ]

    def get_entry(self, doc_id: str) -> dict[str, Any] | None:
        for saved_id, document, metadata in self.items:
            if saved_id == doc_id:
                return {"id": saved_id, "document": document, "metadata": metadata}
        return None

    def mark_superseded(self, doc_id: str, superseded_by: str) -> bool:
        for index, (saved_id, document, metadata) in enumerate(self.items):
            if saved_id == doc_id:
                updated = dict(metadata)
                updated["superseded_by"] = superseded_by
                self.items[index] = (saved_id, document, updated)
                return True
        return False

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        return [
            {"document": doc, "metadata": meta}
            for _, doc, meta in self.items[:n_results]
        ]


def test_store_interview_note_persists_with_metadata():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    doc_id = agent.store_interview_note(
        run_id="run-abc",
        memory_session_id="session-abc",
        content="Take memo first, then small key appears on mantelpiece.",
        reason="User requested saving faster parlor route.",
    )

    assert doc_id.startswith("interview-run-abc-")
    assert len(store.items) == 1
    saved_id, document, metadata = store.items[0]
    assert saved_id == doc_id
    assert "memo first" in document
    assert metadata["source"] == "agent_chat"
    assert metadata["run_id"] == "run-abc"
    assert metadata["memory_session_id"] == "session-abc"
    assert "created_at" in metadata


def test_store_interview_note_supersedes_older_agent_chat():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]

    old_id = agent.store_interview_note(
        run_id="run-old",
        memory_session_id="session-abc",
        content="Old speedrun with hook and rope.",
        reason="First attempt.",
    )
    new_id = agent.store_interview_note(
        run_id="run-new",
        memory_session_id="session-abc",
        content="New 3-step path: take key, unlock door, escape.",
        reason="Corrected route after interview.",
        supersedes=[old_id],
    )

    old_entry = store.get_entry(old_id)
    assert old_entry is not None
    assert old_entry["metadata"]["superseded_by"] == new_id

    context, hits = agent.get_context("session-abc")
    assert "Old speedrun with hook and rope." not in context
    assert "New 3-step path" in context
    assert len(hits) == 1


def test_interview_prompt_mentions_save_to_memory():
    from agent.interview import INTERVIEW_SYSTEM_PROMPT

    assert "save_to_memory" in INTERVIEW_SYSTEM_PROMPT
    assert "Be proactive" in INTERVIEW_SYSTEM_PROMPT
    assert "do not wait to be asked" in INTERVIEW_SYSTEM_PROMPT
    assert "solution paths" in INTERVIEW_SYSTEM_PROMPT
    assert "playbook" in INTERVIEW_SYSTEM_PROMPT
    assert "Authoritative command index" in INTERVIEW_SYSTEM_PROMPT
    assert "supersedes" in INTERVIEW_SYSTEM_PROMPT
    assert "{command_index}" in INTERVIEW_SYSTEM_PROMPT
    assert "{memory_index}" in INTERVIEW_SYSTEM_PROMPT


def test_explorer_prompt_includes_memory_priority_rules():
    from agent.prompts import EXPLORER_BASE_PROMPT

    assert "Memory priority (critical)" in EXPLORER_BASE_PROMPT
    assert "Memory as next-run playbook (critical)" in EXPLORER_BASE_PROMPT
    assert "cannot write to memory during this run" in EXPLORER_BASE_PROMPT
    assert "oldest first" in EXPLORER_BASE_PROMPT
    assert "Step budget (critical)" in EXPLORER_BASE_PROMPT


def test_build_explorer_prompt_includes_step_budget():
    from agent.prompts import build_explorer_prompt

    prompt = build_explorer_prompt("openai/gpt-4o-mini", "", max_steps=42)
    assert "budget of 42 send_command calls" in prompt
