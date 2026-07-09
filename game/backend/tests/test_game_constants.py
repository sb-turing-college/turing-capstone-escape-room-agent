"""Tests for shared game_constants command vocabulary."""

from __future__ import annotations

from game.game_constants import (
    available_verbs,
    syntax_patterns,
    unknown_verb_message,
    verb_default_fallback,
)


def test_available_verbs_include_touch_pull_speak():
    verbs = available_verbs()
    for verb in ("touch", "pull", "speak", "look around", "inventory"):
        assert verb in verbs


def test_unknown_verb_message_includes_use_with_pattern_and_touch():
    message = unknown_verb_message()
    assert message.startswith("Unknown command.")
    assert "use x with y" in message
    assert "touch" in message


def test_touch_default_fallback_is_neutral_english():
    assert verb_default_fallback("touch") == "Ordinary to the touch."


def test_syntax_patterns_are_non_empty_strings():
    assert syntax_patterns()
    assert all(isinstance(pattern, str) and pattern for pattern in syntax_patterns())
