"""Tests for in-process EventBus."""

from __future__ import annotations

import asyncio

import pytest

from event_bus import EventBus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.mark.asyncio
async def test_subscriber_receives_published_event(bus: EventBus):
    queue = await bus.subscribe("run-1")
    await bus.publish("run-1", {"type": "thought", "content": "hello"})
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event["type"] == "thought"
    assert event["content"] == "hello"


@pytest.mark.asyncio
async def test_late_subscriber_gets_backlog(bus: EventBus):
    await bus.publish("run-2", {"type": "action", "step": 1})
    await bus.publish("run-2", {"type": "action", "step": 2})
    queue = await bus.subscribe("run-2")
    first = await asyncio.wait_for(queue.get(), timeout=1.0)
    second = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert first["step"] == 1
    assert second["step"] == 2


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery(bus: EventBus):
    queue = await bus.subscribe("run-3")
    await bus.unsubscribe("run-3", queue)
    await bus.publish("run-3", {"type": "ping"})
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.05)


@pytest.mark.asyncio
async def test_history_is_capped(bus: EventBus):
    bus._max_history = 3
    for i in range(5):
        await bus.publish("run-4", {"type": "thought", "step": i})
    assert len(bus._history["run-4"]) == 3
    assert bus._history["run-4"][0]["step"] == 2
