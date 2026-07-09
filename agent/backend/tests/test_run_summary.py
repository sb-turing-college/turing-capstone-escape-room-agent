"""Tests for run summary storage (memory_stored content)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent.memory_agent import MemoryAgent, RUN_SUMMARY_MAX_TOKENS, build_llm


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

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        return [
            {"document": doc, "metadata": meta}
            for _, doc, meta in self.items[:n_results]
        ]


class _BlockResponse:
    content = [
        {
            "type": "text",
            "text": "- Opened lockbox with small key.\n- Note shows codes 482 and 617.",
        }
    ]


LONG_REFLECTION = (
    "I've reached the step limit. Progress: opened lockbox, found codes 482 and 617, "
    "grate still locked, hook and rope may combine for chimney access."
)


@pytest.mark.asyncio
async def test_store_run_summary_uses_agent_reflection_without_llm():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]
    agent.llm = AsyncMock()
    agent.llm.ainvoke = AsyncMock()

    document, source = await agent.store_run_summary(
        run_id="run-abc",
        steps=[
            {"type": "thought", "content": LONG_REFLECTION},
            {"type": "observation", "content": "You open the lockbox."},
        ],
        success=False,
        explorer_model="test/model",
        memory_session_id="session-abc",
        last_state={"room": "parlor", "inventory": ["rope"], "ending": None},
        commands_used=20,
        max_commands=20,
    )

    agent.llm.ainvoke.assert_not_called()
    assert source == "in_game_reflection"
    assert LONG_REFLECTION in document
    assert "room: parlor" in document
    assert store.items[0][2]["source"] == "in_game_reflection"


@pytest.mark.asyncio
async def test_store_run_summary_llm_fallback_when_no_thought():
    store = _FakeChromaStore()
    agent = MemoryAgent(store, "test/model")  # type: ignore[arg-type]
    agent.llm = AsyncMock()
    agent.llm.ainvoke = AsyncMock(return_value=_BlockResponse())

    document, source = await agent.store_run_summary(
        run_id="run-abc",
        steps=[{"type": "observation", "content": "You open the lockbox."}],
        success=False,
        explorer_model="test/model",
        memory_session_id="session-abc",
        last_state={"room": "library", "inventory": [], "ending": None},
        commands_used=5,
        max_commands=20,
    )

    agent.llm.ainvoke.assert_called_once()
    assert source == "fallback_summary"
    assert "482 and 617" in document
    assert "room: library" in document
    assert store.items[0][2]["source"] == "fallback_summary"


def test_memory_agent_llm_uses_summary_token_budget():
    llm = build_llm("test/model", max_tokens=RUN_SUMMARY_MAX_TOKENS, exclude_reasoning=True)
    assert llm.max_tokens == RUN_SUMMARY_MAX_TOKENS
    assert llm.extra_body == {"reasoning": {"exclude": True}}
