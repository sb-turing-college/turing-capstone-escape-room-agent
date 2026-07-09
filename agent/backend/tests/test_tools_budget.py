"""Tests for command budget fields in tool responses."""

from __future__ import annotations

import json

import pytest

from agent.tools import RunContext


class _FakeGameClient:
    async def send_command(self, command: str) -> dict:
        return {"room": "library", "text": "ok", "visible_items": [], "inventory": [], "exits": {}}

    async def get_state(self) -> dict:
        return {"room": "library", "text": "", "visible_items": [], "inventory": [], "exits": {}}


@pytest.mark.asyncio
async def test_send_command_includes_budget_after_action():
    context = RunContext(_FakeGameClient(), max_commands=50)  # type: ignore[arg-type]
    raw = await context.send_command("look around")
    payload = json.loads(raw)

    assert payload["commands_used"] == 1
    assert payload["commands_remaining"] == 49
    assert payload["room"] == "library"


@pytest.mark.asyncio
async def test_send_command_at_limit_returns_zero_remaining():
    context = RunContext(_FakeGameClient(), max_commands=1)  # type: ignore[arg-type]
    await context.send_command("look around")
    raw = await context.send_command("look around")
    payload = json.loads(raw)

    assert payload["error"] == "Step limit reached for this run."
    assert payload["commands_used"] == 1
    assert payload["commands_remaining"] == 0


@pytest.mark.asyncio
async def test_get_state_includes_budget_without_increment():
    context = RunContext(_FakeGameClient(), max_commands=10)  # type: ignore[arg-type]
    raw = await context.get_state()
    payload = json.loads(raw)

    assert payload["commands_used"] == 0
    assert payload["commands_remaining"] == 10
