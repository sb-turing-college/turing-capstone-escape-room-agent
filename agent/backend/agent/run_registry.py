"""Run lifecycle registry: stop, pause, and human-in-the-loop responses."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

_active_runs: dict[str, asyncio.Event] = {}

# "Give Hint" / ask_human human-in-the-loop pause (Section 4): mirrors the stop-event
# registry above. `_pause_events[run_id]` is set while a pause is requested
# *or* active; `_resume_events[run_id]` is what the paused round loop waits
# on to continue. Both are cleared/removed once the run finishes.
#
# The actual wait happens inside the send_command/get_state tool itself
# (see RunContext.on_before_action in tools.py) or inside ask_human — models
# that chain many tool calls inside a single round would otherwise not see a
# pause for a long time.
_pause_events: dict[str, asyncio.Event] = {}
_resume_events: dict[str, asyncio.Event] = {}
_pending_human_response: dict[str, str | None] = {}


@dataclass
class PauseContext:
    initiator: Literal["human", "agent"]
    agent_theory: str | None = None
    agent_question: str | None = None


_pause_context: dict[str, PauseContext | None] = {}


def register_run_cancellation(run_id: str) -> asyncio.Event:
    """Register a stop event for an active run; returned event is set on cancel."""
    stop_event = asyncio.Event()
    _active_runs[run_id] = stop_event
    return stop_event


def cancel_run(run_id: str) -> bool:
    """Signal a running run to stop. Returns False if not active or already stopping."""
    stop = _active_runs.get(run_id)
    if stop and not stop.is_set():
        stop.set()
        return True
    return False


def register_run_pause(run_id: str) -> None:
    _pause_events[run_id] = asyncio.Event()
    _resume_events[run_id] = asyncio.Event()
    _pending_human_response[run_id] = None
    _pause_context[run_id] = None


def is_run_paused(run_id: str) -> bool:
    event = _pause_events.get(run_id)
    return bool(event and event.is_set())


def get_pause_context(run_id: str) -> PauseContext | None:
    return _pause_context.get(run_id)


def request_pause(
    run_id: str,
    *,
    initiator: Literal["human", "agent"] = "human",
    agent_theory: str | None = None,
    agent_question: str | None = None,
) -> bool:
    """Ask a running run to pause. Returns False if not registered or already paused."""
    pause_event = _pause_events.get(run_id)
    if pause_event is None or pause_event.is_set():
        return False
    _pause_context[run_id] = PauseContext(
        initiator=initiator,
        agent_theory=agent_theory,
        agent_question=agent_question,
    )
    pause_event.set()
    resume_event = _resume_events.get(run_id)
    if resume_event is not None:
        resume_event.clear()
    return True


def submit_human_response_and_resume(run_id: str, human_response: str | None) -> bool:
    """Deliver an optional human response and wake a paused run."""
    pause_event = _pause_events.get(run_id)
    resume_event = _resume_events.get(run_id)
    if pause_event is None or resume_event is None or not pause_event.is_set():
        return False
    if human_response is not None and human_response.strip():
        _pending_human_response[run_id] = human_response.strip()
    else:
        _pending_human_response[run_id] = ""
    pause_event.clear()
    resume_event.set()
    return True


def submit_hint_and_resume(run_id: str, hint: str | None) -> bool:
    """Backward-compatible alias for submit_human_response_and_resume."""
    return submit_human_response_and_resume(run_id, hint)


def consume_human_response(run_id: str) -> str | None:
    """Pop the human response delivered on resume (may be empty string)."""
    return _pending_human_response.pop(run_id, None)


def clear_pause_context(run_id: str) -> None:
    _pause_context[run_id] = None


def format_agent_human_observation(response: str | None) -> str:
    if response and response.strip():
        return f"[Human response: {response.strip()}]"
    return (
        "[Human chose not to respond. Continue without assuming human help. "
        "Do not ask the same question again.]"
    )


def format_human_hint_observation(response: str | None) -> str | None:
    if response and response.strip():
        return f"Hint from the human observer watching this run: {response.strip()}"
    return None


def cleanup_run(run_id: str) -> None:
    _active_runs.pop(run_id, None)
    _pause_events.pop(run_id, None)
    _resume_events.pop(run_id, None)
    _pending_human_response.pop(run_id, None)
    _pause_context.pop(run_id, None)
