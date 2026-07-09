"""Shared pytest fixtures for capstone-game backend tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from game.engine import GameSession


@pytest.fixture
def session_in() -> Callable[..., GameSession]:
    def factory(room: str, inventory: list[str] | None = None) -> GameSession:
        session = GameSession()
        session.state.current_room = room
        if inventory is not None:
            session.state.inventory = list(inventory)
        return session

    return factory
