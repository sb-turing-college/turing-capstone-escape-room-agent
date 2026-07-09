"""Tests for run_registry pause/stop/hint lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from agent.run_registry import (
    cancel_run,
    cleanup_run,
    is_run_paused,
    register_run_cancellation,
    register_run_pause,
    request_pause,
    submit_human_response_and_resume,
)


@pytest.fixture
def run_id() -> str:
    rid = "test-run-registry"
    register_run_cancellation(rid)
    register_run_pause(rid)
    yield rid
    cleanup_run(rid)


def test_cancel_run_sets_stop_event(run_id: str):
    stop = register_run_cancellation(run_id)
    assert cancel_run(run_id) is True
    assert stop.is_set()
    assert cancel_run(run_id) is False


def test_pause_and_resume_with_hint(run_id: str):
    assert request_pause(run_id, initiator="human") is True
    assert is_run_paused(run_id) is True
    assert submit_human_response_and_resume(run_id, "try the grate") is True
    assert is_run_paused(run_id) is False


def test_agent_pause_stores_context(run_id: str):
    assert request_pause(
        run_id,
        initiator="agent",
        agent_theory="Stuck on safe puzzle.",
        agent_question="How many digits?",
    )
    from agent.run_registry import get_pause_context

    ctx = get_pause_context(run_id)
    assert ctx is not None
    assert ctx.initiator == "agent"
    assert ctx.agent_question == "How many digits?"


def test_second_pause_request_rejected(run_id: str):
    assert request_pause(run_id, initiator="human") is True
    assert request_pause(run_id, initiator="agent", agent_question="x?") is False


def test_resume_without_hint(run_id: str):
    request_pause(run_id, initiator="human")
    assert submit_human_response_and_resume(run_id, None) is True
    assert is_run_paused(run_id) is False


def test_pause_unknown_run():
    assert request_pause("nonexistent-run") is False


def test_cleanup_removes_registry_entries(run_id: str):
    request_pause(run_id)
    cleanup_run(run_id)
    assert is_run_paused(run_id) is False
    assert cancel_run(run_id) is False


def test_stop_event_can_be_awaited(run_id: str):
    stop = register_run_cancellation(run_id)

    async def waiter() -> bool:
        await asyncio.wait_for(stop.wait(), timeout=1.0)
        return True

    cancel_run(run_id)
    assert asyncio.run(waiter()) is True
