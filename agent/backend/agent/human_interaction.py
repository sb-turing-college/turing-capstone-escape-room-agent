"""Persist human hints and responses as typed step records."""

from __future__ import annotations

from typing import Any

from agent.callbacks import emit_custom_event

HUMAN_HINT = "human_hint"
HUMAN_RESPONSE = "human_response"


def interaction_type_for_initiator(initiator: str) -> str:
    """Map pause initiator to the step type used for persisted human input."""
    return HUMAN_RESPONSE if initiator == "agent" else HUMAN_HINT


async def emit_human_interaction_step(
    db: Any,
    run_id: str,
    publish: Any,
    step_counter: list[int],
    *,
    text: str,
    interaction_type: str,
    room: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Persist one human_hint or human_response step with raw observer text."""
    cleaned = text.strip()
    if not cleaned:
        return
    if interaction_type not in (HUMAN_HINT, HUMAN_RESPONSE):
        raise ValueError(f"Unknown interaction_type: {interaction_type}")
    await emit_custom_event(
        db,
        run_id,
        publish,
        interaction_type,
        cleaned,
        step_counter,
        room=room,
        extra=extra,
    )
