"""Room description mentions update when items are taken or revealed."""

from __future__ import annotations

from game.engine import GameSession


def _session_in_parlor() -> GameSession:
    session = GameSession()
    session.state.current_room = "parlor"
    return session


class TestParlorRoomMentions:
    def test_memo_mentioned_before_taking(self):
        session = _session_in_parlor()
        result = session.execute("look around")
        assert "crumpled memo" in result.text
        assert "small key" not in result.text.lower()

    def test_memo_removed_from_text_after_taking(self):
        session = _session_in_parlor()
        session.execute("take memo")
        result = session.execute("look around")
        assert "crumpled memo" not in result.text
        assert "note_memo" not in result.visible_items
        assert ". above" not in result.text.lower()
        assert "fireplace" in result.text.lower()

    def test_small_key_appears_after_memo_taken(self):
        session = _session_in_parlor()
        session.execute("take memo")
        result = session.execute("look around")
        assert "small key" in result.text.lower()
        assert "small_key" in result.visible_items

    def test_small_key_removed_from_text_after_taking(self):
        session = _session_in_parlor()
        session.execute("take memo")
        session.execute("take small key")
        result = session.execute("look around")
        assert "small key" not in result.text.lower()
        assert "small_key" not in result.visible_items

    def test_small_key_mention_spaced_after_chimney_ladder_text(self):
        session = _session_in_parlor()
        session.execute("take memo")
        session.execute("speak fiend")
        result = session.execute("look around")
        assert "red. A small key" in result.text
        assert "red.A" not in result.text

    def test_chainsaw_removed_from_text_after_taking(self):
        session = _session_in_parlor()
        session.execute("take chainsaw")
        result = session.execute("look around")
        assert "chainsaw" not in result.text.lower()
        assert "chainsaw" not in result.visible_items
