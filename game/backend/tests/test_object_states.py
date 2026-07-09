"""Room-scoped object_states in API responses."""

from __future__ import annotations

from game.engine import GameSession


def test_object_states_scoped_to_current_room():
    session = GameSession()

    library = session.get_state()
    assert session.state.current_room == "library"
    assert set(library.object_states.keys()) == {"door", "lockbox"}
    assert "painting" not in library.object_states
    assert "safe" not in library.object_states
    assert "grate" not in library.object_states

    session.state.set_flag("door_unlocked", True)
    session.state.set_flag("door_open", True)
    session.execute("go south")
    parlor = session.get_state()
    assert session.state.current_room == "parlor"
    assert set(parlor.object_states.keys()) == {"grate"}
    assert "painting" not in parlor.object_states
    assert "lockbox" not in parlor.object_states


def test_object_states_hides_safe_until_painting_open():
    session = GameSession()
    session.state.current_room = "lords_office"

    state = session.get_state()
    assert state.object_states == {}
    assert "painting" not in state.object_states
    assert "safe" not in state.object_states


def test_object_states_in_lords_office_includes_painting_and_safe():
    session = GameSession()
    session.state.current_room = "lords_office"
    session.state.set_flag("painting_open", True)

    state = session.get_state()
    assert set(state.object_states.keys()) == {"painting", "safe"}
    assert state.object_states["painting"] == "open"
    assert state.object_states["safe"] == "locked"
