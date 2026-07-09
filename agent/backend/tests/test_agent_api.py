"""API smoke tests for agent backend."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(api_client: TestClient):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_endpoint(api_client: TestClient):
    response = api_client.get("/agent/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)


def test_runs_list_empty_ok(api_client: TestClient):
    response = api_client.get("/agent/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
