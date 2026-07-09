"""Tests for the reworked grappling-hook/grate mechanic (Phase 5b).

Using the grappling hook on the grate no longer teleports the player into
Lord's Office directly - it only unlocks the "south-west" exit (in
both directions) and leaves the grappling hook behind as a visible fixture
on the grate. Reaching Lord's Office then requires an explicit `go`.
"""

from __future__ import annotations

from game.engine import GameSession


def _session_in(room: str, inventory: list[str] | None = None) -> GameSession:
    session = GameSession()
    session.state.current_room = room
    for item in inventory or []:
        session.state.add_item(item)
    return session


class TestUseGrapplingHookOnGrate:
    def test_requires_the_grappling_hook_in_inventory(self):
        session = _session_in("parlor")
        result = session.execute("use grappling hook with grate")
        assert "don't have" in result.text.lower()
        assert session.state.flag("grate_open") is False

    def test_using_it_opens_the_grate_without_moving_the_player(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        result = session.execute("use grappling hook with grate")
        assert session.state.flag("grate_open") is True
        assert session.state.current_room == "parlor"
        assert result.room == "parlor"

    def test_using_it_consumes_the_grappling_hook_from_inventory(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        session.execute("use grappling hook with grate")
        assert "grappling_hook" not in session.state.inventory

    def test_using_it_twice_reports_already_fixed(self):
        # already_flag is checked before needs_inventory, so this reports
        # "already fixed" even though the hook was consumed by the first use.
        session = _session_in("parlor", inventory=["grappling_hook"])
        session.execute("use grappling hook with grate")
        result = session.execute("use grappling hook with grate")
        assert result.text == "The grappling hook is already fixed to the top of the grate."


class TestHookOnGrateVisibility:
    def test_fixture_hidden_before_grate_is_opened(self):
        session = _session_in("parlor")
        result = session.execute("look around")
        assert "hook_on_grate" not in result.visible_items

    def test_fixture_visible_after_grate_is_opened(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        session.execute("use grappling hook with grate")
        result = session.execute("look around")
        assert "hook_on_grate" in result.visible_items

    def test_grate_object_state_reflects_open(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        result = session.execute("use grappling hook with grate")
        assert result.object_states["grate"] == "open"


class TestSouthWestExit:
    def test_blocked_before_grate_is_opened(self):
        session = _session_in("parlor")
        result = session.execute("go south-west")
        assert result.room == "parlor"
        assert "grate" in result.text.lower()

    def test_go_grate_object_alias_blocked_before_open(self):
        session = _session_in("parlor")
        result = session.execute("go grate")
        assert result.room == "parlor"

    def test_open_after_grate_is_opened(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        session.execute("use grappling hook with grate")
        result = session.execute("go south-west")
        assert result.room == "lords_office"

    def test_go_grate_object_alias_works_after_open(self):
        session = _session_in("parlor", inventory=["grappling_hook"])
        session.execute("use grappling hook with grate")
        result = session.execute("go grate")
        assert result.room == "lords_office"

    def test_return_trip_north_east_always_open(self):
        # The only way into lords_office is via the (now open) grate, so
        # this exit was never gated - confirm it still just works.
        session = _session_in("lords_office")
        result = session.execute("go north-east")
        assert result.room == "parlor"
