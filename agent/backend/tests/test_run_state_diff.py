"""Tests for run_state_diff map events."""

from __future__ import annotations

from agent.run_state_diff import diff_state


def test_diff_state_initial_room_and_items():
    current = {"room": "library", "visible_items": ["lockbox", "brass_key"]}
    events = diff_state(None, current)
    types = [e["type"] for e in events]
    assert types[0] == "room_visited"
    assert events[0]["room"] == "library"
    assert events[0]["label"] == "The Library"
    assert types.count("item_discovered") == 2


def test_diff_state_room_change():
    previous = {"room": "library", "visible_items": ["lockbox"]}
    current = {"room": "parlor", "visible_items": ["grate"]}
    events = diff_state(previous, current)
    assert any(e["type"] == "room_visited" and e["room"] == "parlor" for e in events)


def test_diff_state_new_visible_item_only():
    previous = {"room": "library", "visible_items": ["lockbox"]}
    current = {"room": "library", "visible_items": ["lockbox", "note_code"]}
    events = diff_state(previous, current)
    discovered = [e for e in events if e["type"] == "item_discovered"]
    assert len(discovered) == 1
    assert discovered[0]["item"] == "note_code"
