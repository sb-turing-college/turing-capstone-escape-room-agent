"""In-process pub/sub for WebSocket run events."""

from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._max_history = 500
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._queues.setdefault(run_id, []).append(queue)
            backlog = list(self._history.get(run_id, []))
        for event in backlog:
            await queue.put(event)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            listeners = self._queues.get(run_id, [])
            if queue in listeners:
                listeners.remove(queue)
            if not listeners:
                self._queues.pop(run_id, None)

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            history = self._history.setdefault(run_id, [])
            history.append(event)
            if len(history) > self._max_history:
                del history[: len(history) - self._max_history]
            listeners = list(self._queues.get(run_id, []))
        for queue in listeners:
            await queue.put(event)


event_bus = EventBus()
