"""Tests for safe combination hint and `use safe <number>` syntax."""

from __future__ import annotations

from game.content import SAFE_CODE_HINT
from game.engine import GameSession


def _session_with_visible_safe() -> GameSession:
    session = GameSession()
    session.state.current_room = "lords_office"
    session.state.set_flag("painting_open", True)
    return session


class TestSafeCodeHint:
    def test_examine_locked_safe_shows_hint(self):
        session = _session_with_visible_safe()
        result = session.execute("examine safe")
        assert result.text == SAFE_CODE_HINT

    def test_use_locked_safe_shows_hint(self):
        session = _session_with_visible_safe()
        result = session.execute("use safe")
        assert result.text == SAFE_CODE_HINT

    def test_open_locked_safe_shows_hint(self):
        session = _session_with_visible_safe()
        result = session.execute("open safe")
        assert result.text == SAFE_CODE_HINT

    def test_use_safe_number_unlocks(self):
        session = _session_with_visible_safe()
        result = session.execute("use safe 617482")
        assert "combination is correct" in result.text
        assert session.state.flag("safe_unlocked")

    def test_use_safe_with_number_literal_shows_fake_number_message(self):
        session = _session_with_visible_safe()
        result = session.execute("use safe with number")
        assert result.text == "Nice try. Enter a real number."

    def test_use_safe_number_literal_shows_fake_number_message(self):
        session = _session_with_visible_safe()
        result = session.execute("use safe number")
        assert result.text == "Nice try. Enter a real number."

    def test_use_safe_with_number_still_unlocks(self):
        session = _session_with_visible_safe()
        result = session.execute("use safe with 617482")
        assert "combination is correct" in result.text
        assert session.state.flag("safe_unlocked")
