"""Smoke tests for game client (requires running capstone-game backend)."""

from __future__ import annotations

import os

import pytest

from agent.game_client import GameClient

GAME_URL = os.getenv("GAME_API_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
async def client():
    game = GameClient(GAME_URL)
    yield game
    await game.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_game_health_and_new_game(client: GameClient):
    if not await client.health_check():
        pytest.skip("Game API not running – start capstone-game backend on port 8000")

    state = await client.new_game()
    assert state["room"] == "library"
    assert isinstance(state["visible_items"], list)
    assert client.session_id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_game_action_contract(client: GameClient):
    if not await client.health_check():
        pytest.skip("Game API not running")

    await client.new_game()
    state = await client.send_command("look around")
    assert "text" in state
    assert state["room"] == "library"
