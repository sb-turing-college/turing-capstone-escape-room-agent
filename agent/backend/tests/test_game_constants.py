"""Tests for synced game_constants.json (source: capstone-game/shared/)."""

from __future__ import annotations

from game_constants import load_game_constants, room_label


def test_game_constants_has_required_sections():
    data = load_game_constants()
    for key in (
        "room_labels",
        "item_labels",
        "direction_labels",
        "room_positions",
        "room_use_extras",
        "commands",
    ):
        assert key in data
        assert isinstance(data[key], dict)
        assert data[key]

    commands = data["commands"]
    assert "verbs" in commands
    assert "touch" in commands["verbs"]
    assert "pull" in commands["verbs"]


def test_room_label_known_rooms():
    assert room_label("library") == "The Library"
    assert room_label("unknown_room") == "unknown_room"
