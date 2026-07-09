"""Save/load slots and export/restore API tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from db.database import SessionLocal, init_db
from db.models import SavedGameRecord
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db():
    init_db()
    yield
    db = SessionLocal()
    try:
        db.query(SavedGameRecord).delete()
        db.commit()
    finally:
        db.close()


def _client_id() -> str:
    return f"test-{uuid.uuid4()}"


def _new_session() -> str:
    response = client.post("/game/new")
    assert response.status_code == 200
    return response.json()["session_id"]


class TestExportRestore:
    def test_export_then_restore_preserves_state(self):
        session_id = _new_session()
        client.post(
            f"/game/{session_id}/action",
            json={"command": "take brass key"},
        )
        exported = client.get(f"/game/{session_id}/export-state")
        assert exported.status_code == 200
        payload = exported.json()
        assert "brass_key" in payload["inventory"] or payload.get("taken_from_rooms")

        restore = client.post("/game/restore", json={"state": payload})
        assert restore.status_code == 200
        restored = restore.json()
        assert restored["session_id"] is not None
        assert "brass_key" in restored["inventory"]

    def test_export_unknown_session_404(self):
        response = client.get("/game/missing-session/export-state")
        assert response.status_code == 404


class TestSaveLoad:
    def test_save_load_round_trip(self):
        session_id = _new_session()
        cid = _client_id()

        client.post(
            f"/game/{session_id}/action",
            json={"command": "take brass key"},
        )
        save = client.post(
            f"/game/{session_id}/save/1",
            json={"client_id": cid},
        )
        assert save.status_code == 200
        save_data = save.json()
        assert save_data["slot"] == 1
        assert save_data["room"] == "library"

        client.post(
            f"/game/{session_id}/action",
            json={"command": "examine lockbox"},
        )
        load = client.post(
            f"/game/{session_id}/load/1",
            json={"client_id": cid},
        )
        assert load.status_code == 200
        loaded = load.json()
        assert loaded["session_id"] == session_id
        assert "brass_key" in loaded["inventory"]

    def test_load_empty_slot_404(self):
        session_id = _new_session()
        response = client.post(
            f"/game/{session_id}/load/2",
            json={"client_id": _client_id()},
        )
        assert response.status_code == 404

    def test_invalid_slot_400(self):
        session_id = _new_session()
        response = client.post(
            f"/game/{session_id}/save/9",
            json={"client_id": _client_id()},
        )
        assert response.status_code == 400


class TestListSaves:
    def test_list_saves_shows_empty_and_filled_slots(self):
        session_id = _new_session()
        cid = _client_id()

        empty = client.get("/game/saves", params={"client_id": cid})
        assert empty.status_code == 200
        slots = empty.json()
        assert len(slots) == 3
        assert all(slot["empty"] for slot in slots)

        client.post(f"/game/{session_id}/save/2", json={"client_id": cid})
        filled = client.get("/game/saves", params={"client_id": cid})
        by_slot = {s["slot"]: s for s in filled.json()}
        assert by_slot[2]["empty"] is False
        assert by_slot[2]["room"] == "library"
        assert by_slot[1]["empty"] is True
