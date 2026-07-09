"""Tests for the `examine_image` field on GameObject (Phase 3c: secret book)."""

from __future__ import annotations

from game.engine import GameSession


def _solved_session_in_lords_office() -> GameSession:
    # TEST CHANGE: was `set_flag("is_solved", True)` - renamed to `safe_open`
    # now that `is_solved` reflects the real demo ending, not "safe opened".
    session = GameSession()
    session.state.current_room = "lords_office"
    session.state.set_flag("painting_open", True)
    session.state.set_flag("safe_unlocked", True)
    session.state.set_flag("safe_open", True)
    return session


class TestSecretBookVisibility:
    def test_book_hidden_before_safe_is_solved(self):
        session = GameSession()
        session.state.current_room = "lords_office"
        result = session.execute("look around")
        assert "secret_book" not in result.visible_items

    def test_book_visible_once_safe_is_solved(self):
        session = _solved_session_in_lords_office()
        result = session.execute("look around")
        assert "secret_book" in result.visible_items

    def test_book_no_longer_visible_in_room_once_taken(self):
        session = _solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("look around")
        assert "secret_book" not in result.visible_items
        assert "secret_book" in session.state.inventory


class TestExamineImageField:
    def test_read_book_from_inventory_returns_image_and_text(self):
        session = _solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("read book")
        assert result.text == (
            "You flip through the pages with mysterious symbols and unreadable "
            "gibberish when a certain page catches your notice: a strangely "
            "familiar chimney with hellish flames and a note beside it: "
            '"Speak Fiend and you may enter"'
        )
        assert result.image == "/assets/examine/secret_book_open.png"

    def test_take_book_does_not_return_image(self):
        session = _solved_session_in_lords_office()
        result = session.execute("take book")
        assert result.image is None

    def test_examine_book_from_inventory_does_not_return_image(self):
        session = _solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("examine book")
        assert result.image is None

    def test_examine_book_in_safe_does_not_return_image(self):
        session = _solved_session_in_lords_office()
        result = session.execute("examine book")
        assert result.image is None

    def test_other_objects_have_no_image(self):
        session = _solved_session_in_lords_office()
        result = session.execute("examine safe")
        assert result.image is None

    def test_diary_alias_resolves_to_the_same_book_on_read(self):
        session = _solved_session_in_lords_office()
        session.execute("take book")
        result = session.execute("read diary")
        assert result.image == "/assets/examine/secret_book_open.png"
