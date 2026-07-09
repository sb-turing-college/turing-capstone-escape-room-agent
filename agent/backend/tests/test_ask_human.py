"""Tests for ask_human tool and human assist quota."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.run_registry import (
    PauseContext,
    cleanup_run,
    is_run_paused,
    register_run_cancellation,
    register_run_pause,
    request_pause,
)
from agent.tools import RunContext, build_tools


@pytest.fixture
def run_id() -> str:
    rid = "test-ask-human"
    register_run_cancellation(rid)
    register_run_pause(rid)
    yield rid
    cleanup_run(rid)


@pytest.mark.asyncio
async def test_ask_human_not_registered_when_quota_zero():
    client = MagicMock()
    ctx = RunContext(game_client=client, max_human_assists=0, run_id="x")
    tools = build_tools(ctx)
    names = [t.name for t in tools]
    assert "ask_human" not in names


@pytest.mark.asyncio
async def test_ask_human_registered_when_quota_positive():
    client = MagicMock()
    ctx = RunContext(game_client=client, max_human_assists=2, run_id="x")
    tools = build_tools(ctx)
    assert "ask_human" in [t.name for t in tools]


@pytest.mark.asyncio
async def test_ask_human_returns_human_response(run_id: str):
    client = MagicMock()

    async def fake_wait() -> tuple[str | None, PauseContext | None] | None:
        return ("Safe code is six digits", PauseContext(initiator="agent"))

    ctx = RunContext(
        game_client=client,
        max_human_assists=2,
        max_commands=50,
        run_id=run_id,
        on_tool_event=AsyncMock(),
        on_await_human_pause=fake_wait,
        on_human_assist_used=AsyncMock(),
    )

    result = await ctx.ask_human(
        "I found a safe but cannot decode the memo symbols.",
        "What do the symbols on the memo mean?",
    )
    payload = json.loads(result)
    assert "Human response" in payload["text"]
    assert payload["commands_used"] == 0
    assert payload["commands_remaining"] == 50
    assert payload["human_assists_used"] == 1
    assert payload["human_assists_remaining"] == 1
    assert ctx.human_assists_used == 1


@pytest.mark.asyncio
async def test_ask_human_empty_response_message(run_id: str):
    client = MagicMock()

    async def fake_wait() -> tuple[str | None, PauseContext | None] | None:
        return ("", PauseContext(initiator="agent"))

    ctx = RunContext(
        game_client=client,
        max_human_assists=1,
        run_id=run_id,
        on_tool_event=AsyncMock(),
        on_await_human_pause=fake_wait,
    )

    result = await ctx.ask_human(
        "I found a safe but cannot decode the memo symbols.",
        "What do the symbols mean?",
    )
    payload = json.loads(result)
    assert "chose not to respond" in payload["text"]


@pytest.mark.asyncio
async def test_ask_human_fails_when_already_paused(run_id: str):
    client = MagicMock()
    request_pause(run_id, initiator="human")
    ctx = RunContext(
        game_client=client,
        max_human_assists=2,
        run_id=run_id,
        on_await_human_pause=AsyncMock(),
    )
    result = await ctx.ask_human(
        "I found a safe but cannot decode the memo symbols.",
        "What do the symbols mean?",
    )
    payload = json.loads(result)
    assert payload["error"] == "run_already_paused"
