"""WebSocket handler for live run events."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from event_bus import event_bus

router = APIRouter()


@router.websocket("/ws/{run_id}")
async def run_events(websocket: WebSocket, run_id: str) -> None:
    """Stream run events for ``run_id`` until completion or client disconnect."""
    await websocket.accept()
    queue = await event_bus.subscribe(run_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue
            await websocket.send_json(event)
            if event.get("type") in {"run_complete", "run_failed"}:
                break
    except WebSocketDisconnect:
        pass
    finally:
        # History is intentionally kept on disconnect so reconnecting clients can replay events.
        await event_bus.unsubscribe(run_id, queue)
