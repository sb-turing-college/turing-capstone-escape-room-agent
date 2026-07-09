"""Persist custom run events and publish them to WebSocket subscribers."""

from __future__ import annotations

from db.datetime_utils import utc_now
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from db.models import StepRecord


async def emit_custom_event(
    db: Session,
    run_id: str,
    publish: Any,
    event_type: str,
    content: str,
    step_counter: list[int],
    room: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Persist one step row and publish the same payload to WebSocket subscribers."""
    step_counter[0] += 1
    record = StepRecord(
        run_id=run_id,
        step_number=step_counter[0],
        type=event_type,
        content=content,
        room=room,
        timestamp=utc_now(),
        extra=extra,
    )
    db.add(record)
    db.commit()
    payload: dict[str, Any] = {
        "type": event_type,
        "content": content,
        "step": step_counter[0],
        "room": room,
        "run_id": run_id,
        "id": str(uuid4()),
    }
    if extra:
        payload.update(extra)
    await publish(payload)
