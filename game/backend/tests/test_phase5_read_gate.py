"""Tests for separating `examine` (description) from `read` (content).

`examine` always shows the physical description (`describe_before_taken` for
notes/books). `read` reveals the actual text once the item is held; before
that, readable items prompt the player to take them first.
"""

from __future__ import annotations

from game.engine import GameSession

READ_TAKE_FIRST = "You can't read it from here, better take it first."


class TestNoteMemoReadGate:
    def _session_in_parlor(self) -> GameSession:
        session = GameSession()
        session.state.current_room = "parlor"
        return session

    def test_examine_before_taking_shows_description_only(self):
        session = self._session_in_parlor()
        result = session.execute("examine memo")
        assert result.text == "A crumpled memo."
        assert "Lord Daedaron" not in result.text

    def test_read_before_taking_prompts_to_take_first(self):
        session = self._session_in_parlor()
        result = session.execute("read memo")
        assert result.text == READ_TAKE_FIRST

    def test_take_does_not_reveal_text_beyond_take_message(self):
        session = self._session_in_parlor()
        result = session.execute("take memo")
        assert result.text == "As you take the memo, a small key is being revealed."

    def test_examine_after_taking_still_shows_description_only(self):
        session = self._session_in_parlor()
        session.execute("take memo")
        result = session.execute("examine memo")
        assert result.text == "A crumpled memo."
        assert "Lord Daedaron" not in result.text

    def test_read_after_taking_reveals_full_text(self):
        session = self._session_in_parlor()
        session.execute("take memo")
        result = session.execute("read memo")
        assert "Lord Daedaron" in result.text
        assert "DON'T TOUCH THAT PAINTING" in result.text


class TestNoteCodeReadGate:
    def _session_with_open_lockbox(self) -> GameSession:
        session = GameSession()
        session.state.current_room = "library"
        session.state.set_flag("lockbox_open", True)
        return session

    def test_examine_before_taking_shows_description_only(self):
        session = self._session_with_open_lockbox()
        result = session.execute("examine note")
        assert result.text == "A note with scribbled writing."
        assert "favorite numbers" not in result.text

    def test_read_before_taking_prompts_to_take_first(self):
        session = self._session_with_open_lockbox()
        result = session.execute("read note")
        assert result.text == READ_TAKE_FIRST

    def test_read_after_taking_reveals_the_code(self):
        session = self._session_with_open_lockbox()
        session.execute("take note")
        result = session.execute("read note")
        assert "favorite numbers" in result.text


class TestSecretBookReadGate:
    BOOK_EXAMINE = "A mysterious old book. You have a bad feeling about that."

    def _solved_session_in_lords_office(self) -> GameSession:
        # TEST CHANGE: was `set_flag("is_solved", True)` - renamed to
        # `safe_open` now that `is_solved` reflects the real demo ending,
        # not "safe opened".
        session = GameSession()
        session.state.current_room = "lords_office"
        session.state.set_flag("painting_open", True)
        session.state.set_flag("safe_unlocked", True)
        session.state.set_flag("safe_open", True)
        return session

    def test_examine_in_safe_shows_description_only(self):
        session = self._solved_session_in_lords_office()
        result = session.execute("examine book")
        assert result.text == self.BOOK_EXAMINE
        assert result.image is None

    def test_read_in_safe_prompts_to_take_first(self):
        session = self._solved_session_in_lords_office()
        result = session.execute("read book")
        assert result.text == READ_TAKE_FIRST

    def test_take_does_not_reveal_text_or_image(self):
        session = self._solved_session_in_lords_office()
        result = session.execute("take book")
        assert result.text == "You take the old book from the safe."
        assert result.image is None

    def test_examine_after_taking_still_shows_description_only(self):
        session = self._solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("examine book")
        assert result.text == self.BOOK_EXAMINE
        assert result.image is None

    def test_read_after_taking_reveals_text_and_image(self):
        session = self._solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("read book")
        assert "Speak Fiend" in result.text
        assert result.image == "/assets/examine/secret_book_open.png"
