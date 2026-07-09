"""API contract tests – pins GameResponse shape for the external agent repo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

EXPECTED_FIELDS = {
    "session_id",
    "text",
    "room",
    "visible_items",
    "exits",
    "inventory",
    "is_solved",
    "object_states",
    "available_verbs",
    "image",
    "ending",
}

client = TestClient(app)


def _assert_game_response_shape(data: dict, *, require_session_id: bool = True) -> None:
    assert set(data.keys()) == EXPECTED_FIELDS
    assert isinstance(data["text"], str)
    assert isinstance(data["room"], str)
    assert isinstance(data["visible_items"], list)
    assert isinstance(data["exits"], dict)
    assert isinstance(data["inventory"], list)
    assert isinstance(data["is_solved"], bool)
    assert isinstance(data["object_states"], dict)
    assert isinstance(data["available_verbs"], list)
    if require_session_id:
        assert data["session_id"] is not None
        assert isinstance(data["session_id"], str)
    assert data["image"] is None or isinstance(data["image"], str)
    assert data["ending"] is None or isinstance(data["ending"], str)


class TestGameApiContract:
    def test_new_game_response_shape(self):
        response = client.post("/game/new")
        assert response.status_code == 200
        _assert_game_response_shape(response.json())

    def test_action_response_shape(self):
        new = client.post("/game/new").json()
        session_id = new["session_id"]
        response = client.post(
            f"/game/{session_id}/action",
            json={"command": "look around"},
        )
        assert response.status_code == 200
        data = response.json()
        _assert_game_response_shape(data)
        assert data["session_id"] == session_id

    def test_state_response_shape(self):
        new = client.post("/game/new").json()
        session_id = new["session_id"]
        response = client.get(f"/game/{session_id}/state")
        assert response.status_code == 200
        data = response.json()
        _assert_game_response_shape(data)
        assert data["session_id"] == session_id

    def test_reset_response_shape(self):
        new = client.post("/game/new").json()
        session_id = new["session_id"]
        response = client.post(f"/game/{session_id}/reset")
        assert response.status_code == 200
        _assert_game_response_shape(response.json())
