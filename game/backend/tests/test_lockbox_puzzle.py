"""Lockbox puzzle flow in the library (Phase 1 core puzzle)."""

from __future__ import annotations


class TestLockboxPuzzle:
    def test_brass_key_does_not_unlock_lockbox(self, session_in):
        session = session_in("library")
        session.execute("take brass key")
        result = session.execute("use brass key with lockbox")
        assert "does not fit" in result.text.lower()
        assert not session.state.flag("lockbox_unlocked")

    def test_cannot_open_locked_lockbox(self, session_in):
        session = session_in("library")
        result = session.execute("open lockbox")
        assert "locked" in result.text.lower()
        assert not session.state.flag("lockbox_open")

    def test_small_key_unlocks_then_open_reveals_note(self, session_in):
        session = session_in("library", inventory=["small_key"])
        unlock = session.execute("use small key with lockbox")
        assert session.state.flag("lockbox_unlocked")
        assert "click" in unlock.text.lower()

        opened = session.execute("open lockbox")
        assert session.state.flag("lockbox_open")
        assert "note" in opened.text.lower()

    def test_unlock_is_idempotent(self, session_in):
        session = session_in("library", inventory=["small_key"])
        session.execute("use small key with lockbox")
        again = session.execute("use small key with lockbox")
        assert "already unlocked" in again.text.lower()
