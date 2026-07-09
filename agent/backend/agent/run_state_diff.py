"""Map-event diffing and replay for continued runs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.orm import Session

from agent.callbacks import emit_custom_event
from db.models import StepRecord
from game_constants import room_label


def diff_state(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    """Derive map events (room visits, item discoveries) between two game snapshots."""
    events: list[dict[str, Any]] = []
    if previous is None:
        events.append(
            {
                "type": "room_visited",
                "room": current["room"],
                "label": room_label(current["room"]),
                "from": None,
                "via": "start",
            }
        )
        for item in current.get("visible_items", []):
            events.append(
                {"type": "item_discovered", "item": item, "room": current["room"]}
            )
        return events

    if previous.get("room") != current.get("room"):
        events.append(
            {
                "type": "room_visited",
                "room": current["room"],
                "label": room_label(current["room"]),
                "from": previous.get("room"),
                "via": "movement",
            }
        )

    prev_items = set(previous.get("visible_items", []))
    for item in current.get("visible_items", []):
        if item not in prev_items:
            events.append(
                {"type": "item_discovered", "item": item, "room": current["room"]}
            )
    return events


_MAP_REPLAY_STEP_TYPES = frozenset({"room_visited", "item_discovered"})
MAP_REPLAY_STEP_TYPES = _MAP_REPLAY_STEP_TYPES


async def replay_map_events_from_steps(
    db: Session,
    run_id: str,
    publish: Callable[[dict[str, Any]], Awaitable[None]],
    step_counter: list[int],
    source_steps: list[StepRecord],
) -> None:
    """Seed a continued run's step log (and WS stream) with map events from the parent."""
    for step in source_steps:
        if step.type not in _MAP_REPLAY_STEP_TYPES:
            continue
        extra = {**(step.extra or {}), "replayed": True}
        await emit_custom_event(
            db,
            run_id,
            publish,
            step.type,
            step.content,
            step_counter,
            room=step.room,
            extra=extra,
        )
