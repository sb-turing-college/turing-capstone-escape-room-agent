"""Unit tests for runner helpers and GameClient.restore_session."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.game_client import GameClient
from agent.runner import _count_prior_runs, create_run_record
from db.models import RunRecord


def test_create_run_record_persists_running_status(db_session):
    run = create_run_record(db_session, "explorer/test", "memory/test")
    assert run.id
    assert run.status == "running"
    assert run.explorer_model == "explorer/test"
    assert run.memory_session_id == run.id


def test_create_run_record_persists_max_steps(db_session):
    run = create_run_record(
        db_session, "explorer/test", "memory/test", max_steps=12
    )
    assert run.max_steps == 12


def test_create_run_record_inherits_memory_session(db_session):
    run = create_run_record(
        db_session, "explorer/test", "memory/test", memory_session_id="session-root"
    )
    assert run.memory_session_id == "session-root"
    assert run.id != "session-root"


def test_count_prior_runs_only_completed(db_session):
    db_session.add(
        RunRecord(id="r1", explorer_model="m", memory_model="m", status="completed")
    )
    db_session.add(
        RunRecord(id="r2", explorer_model="m", memory_model="m", status="running")
    )
    db_session.commit()
    assert _count_prior_runs(db_session) == 1


@pytest.mark.asyncio
async def test_restore_session_uses_live_session():
    client = GameClient("http://game.test")
    live_state = {
        "session_id": "sess-1",
        "text": "ok",
        "room": "library",
        "visible_items": [],
        "exits": {},
        "inventory": [],
        "is_solved": False,
        "object_states": {},
        "available_verbs": [],
        "image": None,
        "ending": None,
    }
    client.get_state = AsyncMock(return_value=live_state)

    state, restored = await client.restore_session(session_id="sess-1")
    assert state == live_state
    assert restored is False


@pytest.mark.asyncio
async def test_restore_session_falls_back_to_snapshot():
    client = GameClient("http://game.test")
    snapshot = {"current_room": "parlor", "inventory": [], "flags": {}, "taken_from_rooms": {}}
    restored_state = {
        "session_id": "sess-2",
        "text": "restored",
        "room": "parlor",
        "visible_items": [],
        "exits": {},
        "inventory": [],
        "is_solved": False,
        "object_states": {},
        "available_verbs": [],
        "image": None,
        "ending": None,
    }

    async def fail_get_state():
        raise httpx.HTTPError("gone")

    client.get_state = fail_get_state
    client.restore_state = AsyncMock(return_value=restored_state)

    state, restored = await client.restore_session(
        session_id="dead-session",
        game_state_json=snapshot,
    )
    assert state["session_id"] == "sess-2"
    assert restored is True
    client.restore_state.assert_awaited_once_with(snapshot)


@pytest.mark.asyncio
async def test_restore_session_raises_without_sources():
    client = GameClient("http://game.test")
    with pytest.raises(RuntimeError, match="No session_id"):
        await client.restore_session()
