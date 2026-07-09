"""Tests for the Phase 4a chimney/ladder ending path.

("speak fiend" in the parlor -> Unearthly Ladder appears -> "go down"/"go
ladder" triggers the cinematic ending instead of a normal room change.)
"""

from __future__ import annotations

from game.engine import GameSession


def _session_in(room: str) -> GameSession:
    session = GameSession()
    session.state.current_room = room
    return session


class TestSpeakFiend:
    def test_speak_fiend_reveals_the_ladder(self):
        session = _session_in("parlor")
        result = session.execute("speak fiend")
        assert "ladder" in result.text.lower()
        assert session.state.flag("chimney_ladder_visible") is True

    def test_speak_fiend_works_without_solving_the_safe_first(self):
        # Spec: usable "at any time" - no `is_solved` gate.
        session = _session_in("parlor")
        assert session.state.flag("is_solved") is False
        result = session.execute("speak fiend")
        assert session.state.flag("chimney_ladder_visible") is True
        assert result.ending is None

    def test_speak_fiend_elsewhere_falls_back_to_generic_text(self):
        session = _session_in("library")
        result = session.execute("speak fiend")
        assert result.text == "This doesn't seem to have an effect."
        assert session.state.flag("chimney_ladder_visible") is False

    def test_speak_fiend_twice_reports_already_there(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("speak fiend")
        assert result.text == "The ladder is already there, waiting in the fireplace."

    def test_speak_fiend_is_case_insensitive(self):
        session = _session_in("parlor")
        result = session.execute("Speak FIEND")
        assert session.state.flag("chimney_ladder_visible") is True
        assert result.text != "This doesn't seem to have an effect."


class TestLadderVisibility:
    def test_ladder_hidden_before_speaking_the_word(self):
        session = _session_in("parlor")
        result = session.execute("look around")
        assert "unearthly_ladder" not in result.visible_items

    def test_ladder_visible_after_speaking_the_word(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("look around")
        assert "unearthly_ladder" in result.visible_items


class TestDownExitHidden:
    """Phase 5 follow-up: "down" must not spoil the secret exit as
    "Down: locked" before the player has any way of knowing it exists."""

    def test_down_exit_absent_before_speaking_the_word(self):
        session = _session_in("parlor")
        result = session.execute("look around")
        assert "down" not in result.exits

    def test_down_exit_present_and_open_after_speaking_the_word(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("look around")
        assert result.exits.get("down") == "open"

    def test_other_locked_exits_are_still_shown(self):
        # Regression: only the chimney shaft is hidden while locked - a
        # regular locked exit like the grate must still be listed.
        session = _session_in("parlor")
        result = session.execute("look around")
        assert result.exits.get("south-west") == "locked"


class TestGoDownEnding:
    def test_go_down_before_ladder_exists_is_blocked(self):
        session = _session_in("parlor")
        result = session.execute("go down")
        assert result.ending is None
        assert session.state.current_room == "parlor"

    def test_go_ladder_before_it_exists_is_blocked(self):
        session = _session_in("parlor")
        result = session.execute("go ladder")
        assert result.ending is None

    def test_go_down_after_speaking_the_word_triggers_ending(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("go down")
        assert result.ending == "chapter1"
        # The room is intentionally left unchanged - the frontend takes over
        # with a full-viewport cinematic instead of a normal scene swap.
        assert session.state.current_room == "parlor"

    def test_go_ladder_alias_after_speaking_the_word_triggers_ending(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("go ladder")
        assert result.ending == "chapter1"

    def test_go_unearthly_ladder_full_alias_triggers_ending(self):
        session = _session_in("parlor")
        session.execute("speak fiend")
        result = session.execute("go unearthly_ladder")
        assert result.ending == "chapter1"

    def test_ending_field_is_none_on_unrelated_commands(self):
        session = _session_in("parlor")
        result = session.execute("look around")
        assert result.ending is None
