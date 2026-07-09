"""LLM streaming orchestration for one agent round."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

from agent.run_messages import has_tool_calls, message_text, thought_from_message


async def invoke_agent_with_thoughts(
    executor: Any,
    messages: list,
    config: dict[str, Any],
    *,
    idle_timeout: float,
    stop_event: asyncio.Event,
    emit_thought: Callable[[str], Awaitable[None]],
    command_count_fn: Callable[[], int],
    stuck_idle_sec: float,
    is_paused_fn: Callable[[], bool] = lambda: False,
) -> tuple[dict[str, Any], bool]:
    """Run one agent round via astream_events and emit LLM thoughts as they complete."""
    result: dict[str, Any] | None = None
    stream_buffer: list[str] = []
    text_only_streak = 0
    last_command_count = command_count_fn()
    last_command_at = time.monotonic()
    stuck_detected = False

    stream = executor.astream_events(
        {"messages": messages},
        config=config,
        version="v2",
    )
    stream_iter = stream.__aiter__()

    try:
        while True:
            if stop_event.is_set():
                raise asyncio.CancelledError()

            try:
                event = await asyncio.wait_for(stream_iter.__anext__(), timeout=idle_timeout)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError as exc:
                if is_paused_fn():
                    continue
                raise RuntimeError(
                    f"No agent activity for {idle_timeout}s "
                    f"({command_count_fn()} game commands so far)"
                ) from exc

            current_commands = command_count_fn()
            if current_commands > last_command_count:
                last_command_count = current_commands
                last_command_at = time.monotonic()
                text_only_streak = 0

            kind = event.get("event")
            if kind == "on_chat_model_start":
                stream_buffer.clear()
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                piece = message_text(chunk)
                if piece:
                    stream_buffer.append(piece)
            elif kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                thought = thought_from_message(output, stream_buffer)
                stream_buffer.clear()
                if thought or has_tool_calls(output):
                    await emit_thought(thought)

                if has_tool_calls(output):
                    text_only_streak = 0
                elif message_text(output):
                    text_only_streak += 1

                idle_sec = time.monotonic() - last_command_at
                if text_only_streak >= 2 or (
                    text_only_streak >= 1 and idle_sec >= stuck_idle_sec
                ):
                    stuck_detected = True
                    break
            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, dict) and "messages" in output:
                    result = output
    finally:
        with contextlib.suppress(Exception):
            await stream_iter.aclose()  # type: ignore[attr-defined]

    if result is None:
        if stuck_detected:
            return {"messages": messages}, True
        raise RuntimeError("Agent stream finished without message output")
    return result, stuck_detected
