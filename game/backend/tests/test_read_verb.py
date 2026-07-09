"""Tests for the standalone `read` verb."""

from __future__ import annotations

from game.engine import GameSession


class TestReadVerb:
    def test_read_without_target_prompts(self):
        session = GameSession()
        result = session.execute("read")
        assert result.text == "What do you want to read?"

    def test_read_unknown_object(self):
        session = GameSession()
        result = session.execute("read unicorn")
        assert result.text == "There is nothing to read."

    def test_read_non_readable_object(self):
        session = GameSession()
        session.state.current_room = "library"
        result = session.execute("read desk")
        assert result.text == "There is nothing to read."

    def test_unknown_command_lists_pull_and_speak(self):
        session = GameSession()
        result = session.execute("dance")
        assert "pull" in result.text
        assert "speak" in result.text
        assert "read" in result.text
        assert "look around" in result.text

    def test_bare_look_is_unknown(self):
        session = GameSession()
        result = session.execute("look")
        assert result.text.startswith("Unknown command.")
