"""Unit tests for game client response validation."""

from __future__ import annotations

import pytest

from agent.game_client import GameClient


def test_validate_response_accepts_full_contract():
    data = {
        "session_id": "abc",
        "text": "hello",
        "room": "library",
        "visible_items": [],
        "exits": {},
        "inventory": [],
        "is_solved": False,
        "object_states": {},
        "available_verbs": ["examine"],
        "image": None,
        "ending": None,
    }
    assert GameClient.validate_response(data) == data


def test_validate_response_rejects_drift():
    with pytest.raises(ValueError, match="contract drift"):
        GameClient.validate_response({"room": "library"})
