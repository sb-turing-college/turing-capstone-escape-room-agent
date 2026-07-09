"""Tests for agent REST routes (no live LLM/game required)."""

from __future__ import annotations

import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from config import get_settings
from db.models import RunRecord, StepRecord


def test_start_run_without_api_key_returns_400(api_client: TestClient):
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
        get_settings.cache_clear()
        response = api_client.post("/agent/run", json={"max_steps": 5})
        assert response.status_code == 400
        assert "OPENROUTER_API_KEY" in response.json()["detail"]
    get_settings.cache_clear()


def test_get_unknown_run_404(api_client: TestClient):
    response = api_client.get("/agent/run/does-not-exist")
    assert response.status_code == 404


def test_stop_unknown_run_404(api_client: TestClient):
    response = api_client.post("/agent/stop/does-not-exist")
    assert response.status_code == 404


def test_pause_inactive_run_409(api_client: TestClient, api_db_session):
    run_id = f"finished-{uuid.uuid4()}"
    api_db_session.add(
        RunRecord(
            id=run_id,
            explorer_model="test/model",
            memory_model="test/model",
            status="completed",
        )
    )
    api_db_session.commit()

    response = api_client.post(f"/agent/run/{run_id}/pause")
    assert response.status_code == 409


def test_memory_count_and_clear(api_client: TestClient):
    count = api_client.get("/agent/memory/count")
    assert count.status_code == 200
    assert "count" in count.json()

    cleared = api_client.post("/agent/memory/clear")
    assert cleared.status_code == 200
    assert cleared.json()["status"] == "cleared"


def test_memory_list_returns_array(api_client: TestClient):
    response = api_client.get("/agent/memory")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_spectate_session_unknown_run_404(api_client: TestClient):
    response = api_client.get("/agent/run/missing-run/spectate-session")
    assert response.status_code == 404


def test_start_run_passes_hint_to_execute_run(api_client: TestClient, monkeypatch):
    captured: dict = {}

    def fake_execute_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("api.run_routes.execute_run", fake_execute_run)

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        get_settings.cache_clear()
        response = api_client.post(
            "/agent/run",
            json={"max_steps": 20, "max_human_assists": 2, "hint": "Ask by command 10"},
        )
        assert response.status_code == 200
    get_settings.cache_clear()
    assert captured["kwargs"].get("resume_hint") == "Ask by command 10"
    assert captured["args"][3] == 20


def test_start_run_persists_max_steps_on_record(
    api_client: TestClient, api_db_session, monkeypatch
):
    monkeypatch.setattr("api.run_routes.execute_run", lambda *args, **kwargs: None)

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        get_settings.cache_clear()
        response = api_client.post("/agent/run", json={"max_steps": 12})
        assert response.status_code == 200
        run_id = response.json()["run_id"]
    get_settings.cache_clear()

    run = api_db_session.query(RunRecord).filter_by(id=run_id).one()
    assert run.max_steps == 12

    listed = api_client.get("/agent/runs").json()
    assert next(item for item in listed if item["run_id"] == run_id)["max_steps"] == 12


def test_retry_run_creates_linked_attempt(api_client: TestClient, api_db_session, monkeypatch):
    run_id = f"finished-{uuid.uuid4()}"
    api_db_session.add(
        RunRecord(
            id=run_id,
            explorer_model="test/model",
            memory_model="test/model",
            status="completed",
            success=True,
            memory_session_id=run_id,
        )
    )
    api_db_session.commit()

    captured: dict = {}

    def fake_execute_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("api.run_routes.execute_run", fake_execute_run)

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        get_settings.cache_clear()
        response = api_client.post(
            f"/agent/run/{run_id}/retry",
            json={"max_steps": 30, "max_human_assists": 1, "hint": "Try the portrait first"},
        )
        assert response.status_code == 200
    get_settings.cache_clear()
    new_run_id = response.json()["run_id"]
    new_run = api_db_session.query(RunRecord).filter_by(id=new_run_id).one()
    assert new_run.continued_from_run_id == run_id
    assert new_run.is_fresh_attempt is True
    assert new_run.memory_session_id == run_id
    assert captured["kwargs"]["fresh_attempt"] is True
    assert captured["kwargs"].get("resume_from_run_id") is None
    assert captured["kwargs"].get("resume_hint") == "Try the portrait first"
    assert new_run.max_steps == 30


def _send_command_step(run_id: str, step_number: int) -> StepRecord:
    return StepRecord(
        run_id=run_id,
        step_number=step_number,
        type="action",
        content=f"send_command: look {step_number}",
    )


def test_list_runs_cumulative_commands_across_continue_chain(
    api_client: TestClient,
    api_db_session,
):
    run_a = f"run-a-{uuid.uuid4()}"
    run_b = f"run-b-{uuid.uuid4()}"
    api_db_session.add_all(
        [
            RunRecord(
                id=run_a,
                explorer_model="test/model",
                memory_model="test/model",
                status="completed",
                memory_session_id=run_a,
            ),
            RunRecord(
                id=run_b,
                explorer_model="test/model",
                memory_model="test/model",
                status="completed",
                continued_from_run_id=run_a,
                memory_session_id=run_a,
            ),
        ]
    )
    api_db_session.add_all(
        [
            _send_command_step(run_a, 1),
            _send_command_step(run_a, 2),
            _send_command_step(run_b, 1),
        ]
    )
    api_db_session.commit()

    response = api_client.get("/agent/runs")
    assert response.status_code == 200
    by_id = {entry["run_id"]: entry for entry in response.json()}
    assert by_id[run_a]["commands_count"] == 2
    assert by_id[run_a]["cumulative_commands_count"] == 2
    assert by_id[run_b]["commands_count"] == 1
    assert by_id[run_b]["cumulative_commands_count"] == 3

    detail = api_client.get(f"/agent/run/{run_b}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["commands_count"] == 1
    assert body["cumulative_commands_count"] == 3


def test_list_runs_cumulative_resets_at_fresh_attempt(
    api_client: TestClient,
    api_db_session,
):
    run_a = f"run-a-{uuid.uuid4()}"
    run_b = f"run-b-{uuid.uuid4()}"
    run_c = f"run-c-{uuid.uuid4()}"
    api_db_session.add_all(
        [
            RunRecord(
                id=run_a,
                explorer_model="test/model",
                memory_model="test/model",
                status="completed",
                memory_session_id=run_a,
            ),
            RunRecord(
                id=run_b,
                explorer_model="test/model",
                memory_model="test/model",
                status="completed",
                continued_from_run_id=run_a,
                is_fresh_attempt=True,
                memory_session_id=run_a,
            ),
            RunRecord(
                id=run_c,
                explorer_model="test/model",
                memory_model="test/model",
                status="completed",
                continued_from_run_id=run_b,
                memory_session_id=run_a,
            ),
        ]
    )
    api_db_session.add_all(
        [
            _send_command_step(run_a, 1),
            _send_command_step(run_a, 2),
            _send_command_step(run_b, 1),
            _send_command_step(run_c, 1),
            _send_command_step(run_c, 2),
        ]
    )
    api_db_session.commit()

    response = api_client.get("/agent/runs")
    assert response.status_code == 200
    by_id = {entry["run_id"]: entry for entry in response.json()}
    assert by_id[run_a]["cumulative_commands_count"] == 2
    assert by_id[run_b]["cumulative_commands_count"] == 1
    assert by_id[run_c]["cumulative_commands_count"] == 3
    assert by_id[run_b]["is_fresh_attempt"] is True
    assert by_id[run_c]["is_fresh_attempt"] is False
