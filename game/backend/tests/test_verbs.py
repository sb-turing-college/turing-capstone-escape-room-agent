"""Tests for the touch/pull/speak verbs (Phase 3a).

New tests only - see TEST RULES in ARCHITECTURE.md: existing tests are never
modified, and there previously was no pytest suite at all (only the manual
`test_solution.py` walkthrough script), so this file establishes the new
`backend/tests/` convention from scratch.
"""

from __future__ import annotations

import pytest

from game.engine import GameSession


def _session_in(room: str) -> GameSession:
    session = GameSession()
    session.state.current_room = room
    return session


class TestNoTarget:
    def test_touch_without_target_prompts(self):
        session = _session_in("library")
        result = session.execute("touch")
        assert result.text == "What do you want to touch?"

    def test_pull_without_target_prompts(self):
        session = _session_in("library")
        result = session.execute("pull")
        assert result.text == "What do you want to pull?"

    def test_speak_without_target_prompts(self):
        session = _session_in("library")
        result = session.execute("speak")
        assert result.text == "What do you want to speak?"


class TestDefaultFallback:
    def test_touch_unresolvable_word_falls_back(self):
        session = _session_in("library")
        result = session.execute("touch xyzzy")
        assert result.text == "Ordinary to the touch."

    def test_pull_known_object_without_rule_falls_back(self):
        # "bookshelf" is a real object, but no `pull bookshelf` rule exists -
        # touch/pull/speak never say "you don't see any X here" like
        # examine/take do, they just report the generic default text.
        session = _session_in("library")
        result = session.execute("pull bookshelf")
        assert result.text == "This doesn't seem to work."

    def test_speak_unresolvable_word_falls_back_without_crashing(self):
        # NOTE: "fiend" used to be the example here, but it is now a real,
        # meaningful alias (Phase 4a, see test_phase4_chimney.py) - swapped
        # to a genuinely unresolvable word so this test still exercises the
        # generic-fallback path it was written for.
        session = _session_in("parlor")
        result = session.execute("speak xyzzy")
        assert result.text == "This doesn't seem to have an effect."


class TestPaintingInteractions:
    def test_touch_painting_has_flavor_text_and_no_side_effect(self):
        session = _session_in("lords_office")
        result = session.execute("touch painting")
        assert result.text == "You touched the painting - it seemed to move briefly."
        assert session.state.flag("painting_open") is False

    def test_pull_painting_opens_it_like_open_painting(self):
        session = _session_in("lords_office")
        result = session.execute("pull painting")
        assert "hidden hinge" in result.text
        assert session.state.flag("painting_open") is True

    def test_pull_painting_twice_reports_already_open(self):
        session = _session_in("lords_office")
        session.execute("pull painting")
        result = session.execute("pull painting")
        assert result.text == "The painting is already swung aside."

    def test_open_then_pull_also_reports_already_open(self):
        # Confirms open/pull share one rule instead of two independent ones.
        session = _session_in("lords_office")
        session.execute("open painting")
        result = session.execute("pull painting")
        assert result.text == "The painting is already swung aside."

    def test_touch_painting_after_it_is_open_still_gives_flavor_text(self):
        session = _session_in("lords_office")
        session.execute("open painting")
        result = session.execute("touch painting")
        assert result.text == "You touched the painting - it seemed to move briefly."


class TestCaseInsensitivity:
    @pytest.mark.parametrize("command", ["TOUCH PAINTING", "Touch Painting", "touch PAINTING"])
    def test_touch_painting_is_case_insensitive(self, command):
        session = _session_in("lords_office")
        result = session.execute(command)
        assert result.text == "You touched the painting - it seemed to move briefly."

    def test_speak_verb_itself_is_case_insensitive(self):
        session = _session_in("parlor")
        result = session.execute("SPEAK xyzzy")
        assert result.text == "This doesn't seem to have an effect."
