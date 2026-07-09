"""Orchestrates a full agent run with memory, events, and persistence."""

from __future__ import annotations

import asyncio
import logging
from db.datetime_utils import utc_now
from typing import Any
from uuid import uuid4

import contextlib
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from agent.callbacks import emit_custom_event
from agent.explorer import create_explorer_agent
from agent.human_interaction import (
    HUMAN_HINT,
    emit_human_interaction_step,
    interaction_type_for_initiator,
)
from agent.game_client import GameClient
from agent.memory_agent import MemoryAgent
from agent.memory_sources import normalize_memory_source
from agent.run_messages import message_text, rebuild_messages_from_steps, thought_from_message
from agent.run_registry import (
    PauseContext,
    cancel_run,
    cleanup_run,
    clear_pause_context,
    consume_human_response,
    format_human_hint_observation,
    get_pause_context,
    is_run_paused,
    register_run_cancellation,
    register_run_pause,
)
from agent.run_state_diff import diff_state, replay_map_events_from_steps
from agent.run_nudges import (
    build_continue_start_nudge,
    build_fresh_attempt_nudge,
    build_low_budget_ask_human_nudge,
    build_round_continuation_nudge,
    low_budget_command_threshold,
)
from agent.run_stream import invoke_agent_with_thoughts
from agent.tools import RunContext, build_tools
from config import get_settings
from db.database import SessionLocal
from db.models import RunRecord, StepRecord
from event_bus import event_bus
from memory.chroma_store import ChromaStore
from middleware.moderation import moderate_command

def _count_prior_runs(db: Session) -> int:
    return db.query(RunRecord).filter(RunRecord.status == "completed").count()


async def _publish(run_id: str, event: dict[str, Any]) -> None:
    await event_bus.publish(run_id, event)


async def execute_run(
    run_id: str,
    explorer_model: str | None = None,
    memory_model: str | None = None,
    max_steps: int | None = None,
    max_human_assists: int = 0,
    resume_from_run_id: str | None = None,
    resume_hint: str | None = None,
    fresh_attempt: bool = False,
) -> None:
    """Run the explorer agent to completion: game loop, events, DB steps, memory.

    When ``resume_from_run_id`` is set, restores game state from that run and
    rebuilds LangChain message history before continuing with a fresh step budget.

    When ``fresh_attempt`` is True, starts a new game from the library while keeping
    the memory session (and interview chat lineage via ``continued_from_run_id``).
    """
    settings = get_settings()
    explorer_model = explorer_model or str(settings["default_explorer_model"])
    memory_model = memory_model or str(settings["default_memory_model"])
    max_steps = max_steps or int(settings["default_max_steps"])

    max_steps = max_steps or int(settings["default_max_steps"])
    max_human_assists = max(0, min(3, max_human_assists))

    db = SessionLocal()
    stop_event = register_run_cancellation(run_id)
    register_run_pause(run_id)
    step_counter = [0]
    previous_state: dict[str, Any] | None = None

    async def publish_event(event: dict[str, Any]) -> None:
        await _publish(run_id, event)

    async def persist_human_assists_used(used: int) -> None:
        run_row = db.query(RunRecord).filter_by(id=run_id).one_or_none()
        if run_row is not None:
            run_row.human_assists_used = used
            db.commit()

    async def await_human_pause_resolution() -> tuple[str | None, PauseContext | None] | None:
        from agent.run_registry import _pause_events, _resume_events

        pause_event = _pause_events.get(run_id)
        if pause_event is None or not pause_event.is_set():
            return None

        pause_ctx = get_pause_context(run_id) or PauseContext(initiator="human")
        paused_room = (context.last_state or {}).get("room")
        room_str = paused_room if isinstance(paused_room, str) else None

        if pause_ctx.initiator == "agent":
            system_msg = (
                "⏸ Agent paused — waiting for a human response to ask_human."
            )
        else:
            system_msg = "⏸ Run paused — waiting for a hint from the human observer."

        await emit_custom_event(
            db,
            run_id,
            publish_event,
            "system",
            system_msg,
            step_counter,
            room=room_str,
        )
        await _publish(
            run_id,
            {
                "type": "run_paused",
                "run_id": run_id,
                "initiator": pause_ctx.initiator,
                "agent_theory": pause_ctx.agent_theory,
                "agent_question": pause_ctx.agent_question,
                "human_assists_used": context.human_assists_used,
                "max_human_assists": context.max_human_assists,
            },
        )

        resume_event = _resume_events.get(run_id)
        if resume_event is None:
            return None

        while not resume_event.is_set():
            if stop_event.is_set():
                raise asyncio.CancelledError()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(resume_event.wait(), timeout=1.0)

        human_response = consume_human_response(run_id)
        clear_pause_context(run_id)
        resumed_room = (context.last_state or {}).get("room")
        resumed_room_str = resumed_room if isinstance(resumed_room, str) else None
        responded = bool(human_response and human_response.strip())

        if pause_ctx.initiator == "agent":
            resume_system = (
                f"▶ Resumed with human response: {human_response}"
                if responded
                else "▶ Resumed without a human response."
            )
        else:
            resume_system = (
                f"▶ Resumed with human hint: {human_response}"
                if responded
                else "▶ Resumed (no hint given)."
            )

        await emit_custom_event(
            db,
            run_id,
            publish_event,
            "system",
            resume_system,
            step_counter,
            room=resumed_room_str,
        )
        if responded:
            await emit_human_interaction_step(
                db,
                run_id,
                publish_event,
                step_counter,
                text=human_response,
                interaction_type=interaction_type_for_initiator(pause_ctx.initiator),
                room=resumed_room_str,
                extra={"initiator": pause_ctx.initiator},
            )
        await _publish(
            run_id,
            {
                "type": "run_resumed",
                "run_id": run_id,
                "initiator": pause_ctx.initiator,
                "human_response": human_response if responded else None,
                "responded": responded,
                "hint": human_response if responded else None,
            },
        )
        return human_response, pause_ctx

    game_client: GameClient | None = None
    memory_session_id = run_id
    try:
        run = db.query(RunRecord).filter_by(id=run_id).one()
        run.max_human_assists = max_human_assists
        db.commit()
        memory_session_id = run.memory_session_id or run.id
        chroma = ChromaStore(str(settings["chroma_persist_dir"]))
        memory_agent = MemoryAgent(chroma, memory_model)
        memory_context, memory_hits = memory_agent.get_context(
            memory_session_id,
            fresh_attempt=fresh_attempt,
        )

        for hit in memory_hits:
            metadata = hit.get("metadata") or {}
            memory_source = normalize_memory_source(metadata.get("source"))
            await emit_custom_event(
                db,
                run_id,
                publish_event,
                "memory_retrieved",
                hit.get("document", ""),
                step_counter,
                extra={"memory_source": memory_source},
            )

        game_client = GameClient(str(settings["game_api_base_url"]))
        if not await game_client.health_check():
            raise RuntimeError(
                f"Game API unreachable at {settings['game_api_base_url']}. "
                "Start capstone-game backend on port 8000."
            )

        async def on_game_update(state: dict[str, Any]) -> None:
            nonlocal previous_state
            await emit_custom_event(
                db,
                run_id,
                publish_event,
                "game_update",
                state.get("text", ""),
                step_counter,
                room=state.get("room"),
                extra={
                    "visible_items": state.get("visible_items", []),
                    "inventory": state.get("inventory", []),
                    "exits": state.get("exits", {}),
                    "is_solved": state.get("is_solved", False),
                    "ending": state.get("ending"),
                },
            )
            for diff_event in diff_state(previous_state, state):
                await emit_custom_event(
                    db,
                    run_id,
                    publish_event,
                    diff_event["type"],
                    diff_event.get("item") or diff_event.get("label") or diff_event["room"],
                    step_counter,
                    room=state.get("room"),
                    extra=diff_event,
                )
            previous_state = state
            try:
                run.game_state_json = await game_client.export_state()
                db.commit()
            except Exception:
                db.rollback()

        async def on_tool_event(
            event_type: str, content: str, room: str | None
        ) -> None:
            await emit_custom_event(
                db,
                run_id,
                publish_event,
                event_type,
                content,
                step_counter,
                room=room,
            )

        async def on_command_blocked(command: str, reason: str) -> None:
            room = (context.last_state or {}).get("room")
            await emit_custom_event(
                db,
                run_id,
                publish_event,
                "blocked",
                f"Command blocked: '{command}' — {reason}",
                step_counter,
                room=room if isinstance(room, str) else None,
            )

        async def check_human_input() -> str | None:
            """Deliver a pending human pause before the next game action."""
            resolution = await await_human_pause_resolution()
            if resolution is None:
                return None
            human_response, pause_ctx = resolution
            if pause_ctx.initiator != "human":
                return None
            hint_text = format_human_hint_observation(human_response)
            return hint_text

        context = RunContext(
            game_client=game_client,
            on_game_update=on_game_update,
            on_tool_event=on_tool_event,
            on_command_blocked=on_command_blocked,
            on_before_action=check_human_input,
            on_await_human_pause=await_human_pause_resolution,
            on_human_assist_used=persist_human_assists_used,
            moderate=moderate_command,
            max_commands=max_steps,
            max_human_assists=max_human_assists,
            run_id=run_id,
        )
        tools = build_tools(context)
        executor = create_explorer_agent(
            tools,
            explorer_model,
            memory_context,
            max_steps=max_steps,
            max_human_assists=max_human_assists,
        )

        source_run: RunRecord | None = None
        source_steps: list[StepRecord] = []
        if resume_from_run_id:
            source_run = db.query(RunRecord).filter_by(id=resume_from_run_id).one_or_none()
            if source_run is None:
                raise RuntimeError(f"Cannot continue: source run {resume_from_run_id} not found.")

            source_steps = (
                db.query(StepRecord)
                .filter_by(run_id=resume_from_run_id)
                .order_by(StepRecord.step_number)
                .all()
            )

            restored_state, _restored = await game_client.restore_session(
                session_id=source_run.session_id,
                game_state_json=source_run.game_state_json,
            )

            run.session_id = game_client.session_id
            db.commit()
            await replay_map_events_from_steps(
                db, run_id, publish_event, step_counter, source_steps
            )
            previous_state = restored_state
            await on_game_update(restored_state)
        else:
            initial = await game_client.new_game()
            run.session_id = initial["session_id"]
            db.commit()
            await on_game_update(initial)

        max_rounds = max(12, max_steps + 20)
        idle_timeout_sec = int(settings["llm_round_timeout_sec"])
        stuck_idle_sec = int(settings["agent_stuck_idle_sec"])

        await _publish(
            run_id,
            {
                "type": "run_started",
                "run_id": run_id,
                "session_id": run.session_id,
                "explorer_model": explorer_model,
                "continued_from_run_id": run.continued_from_run_id,
                "memory_session_id": memory_session_id,
                "fresh_attempt": fresh_attempt,
                "max_steps": max_steps,
            },
        )

        goal = (
            "Play The Haunted Manor Chapter 0 from the starting room to the demo ending. "
            "Use send_command for every game action. "
            "The run succeeds only when a response JSON contains a non-null \"ending\" field."
        )

        resume_room = (previous_state or {}).get("room")
        resume_room_str = resume_room if isinstance(resume_room, str) else None

        if source_run is not None:
            messages = rebuild_messages_from_steps(source_steps, goal)
            messages.append(
                HumanMessage(
                    content=(
                        "This is a CONTINUATION of a previous run that ended without "
                        "reaching the ending (step limit reached, or stopped). The game "
                        "state above already reflects everything you did before — do NOT "
                        "start over or repeat actions that already succeeded. Continue "
                        "playing with send_command from exactly where you left off."
                    )
                )
            )
            messages.append(
                HumanMessage(
                    content=build_continue_start_nudge(
                        max_steps=max_steps,
                        human_assists_remaining=max_human_assists,
                    )
                )
            )
            if resume_hint:
                messages.append(
                    HumanMessage(
                        content=f"Hint from the human observer watching this run: {resume_hint}"
                    )
                )
                await emit_human_interaction_step(
                    db,
                    run_id,
                    publish_event,
                    step_counter,
                    text=resume_hint,
                    interaction_type=HUMAN_HINT,
                    room=resume_room_str,
                    extra={"source": "resume_hint", "initiator": "human"},
                )
        elif fresh_attempt:
            messages = [HumanMessage(content=goal)]
            nudge = build_fresh_attempt_nudge()
            messages.append(HumanMessage(content=nudge))
            await emit_custom_event(
                db,
                run_id,
                publish_event,
                "system",
                "New attempt — simulation reset; using prior memory as lessons learned.",
                step_counter,
            )
            if resume_hint:
                messages.append(
                    HumanMessage(
                        content=f"Hint from the human observer watching this run: {resume_hint}"
                    )
                )
                await emit_human_interaction_step(
                    db,
                    run_id,
                    publish_event,
                    step_counter,
                    text=resume_hint,
                    interaction_type=HUMAN_HINT,
                    room=resume_room_str,
                    extra={"source": "resume_hint", "initiator": "human"},
                )
        else:
            messages = [HumanMessage(content=goal)]
            if resume_hint:
                messages.append(
                    HumanMessage(
                        content=f"Hint from the human observer watching this run: {resume_hint}"
                    )
                )
                await emit_human_interaction_step(
                    db,
                    run_id,
                    publish_event,
                    step_counter,
                    text=resume_hint,
                    interaction_type=HUMAN_HINT,
                    room=resume_room_str,
                    extra={"source": "resume_hint", "initiator": "human"},
                )
        result: dict[str, Any] = {"messages": messages}
        # Some models return control to the outer loop after nearly every single
        # tool call (one round ≈ one command), while others chain many tool calls
        # inside a single round. Size the round budget for the worst case (1
        # command per round) plus a buffer for non-command rounds (get_state
        # calls, moderation blocks, stuck-recovery nudges) so neither behavior
        # is cut off artificially — the actual game-command limit below is what
        # bounds progress in the common case.

        low_budget_nudge_sent = False
        for round_idx in range(max_rounds):
            if stop_event.is_set():
                raise asyncio.CancelledError()
            if context.success:
                break
            if context.command_count >= max_steps:
                break

            commands_remaining = max(0, max_steps - context.command_count)
            if (
                not low_budget_nudge_sent
                and max_human_assists > 0
                and context.human_assists_remaining() > 0
                and commands_remaining <= low_budget_command_threshold(max_steps)
            ):
                low_budget_nudge_sent = True
                nudge = build_low_budget_ask_human_nudge(
                    commands_remaining,
                    context.human_assists_remaining(),
                )
                await emit_custom_event(
                    db,
                    run_id,
                    publish_event,
                    "system",
                    (
                        "Low send_command budget — nudging ask_human "
                        f"({commands_remaining}/{max_steps} remaining)"
                    ),
                    step_counter,
                    room=(context.last_state or {}).get("room"),
                )
                messages.append(HumanMessage(content=nudge))

            # Fallback checkpoint for rounds that end without any tool call
            # (e.g. a stuck text-only round) — the primary, fast checkpoint is
            # inside the send_command/get_state tool itself (see
            # check_human_input's docstring above).
            fallback_input = await check_human_input()
            if fallback_input:
                messages.append(HumanMessage(content=fallback_input))

            await emit_custom_event(
                db,
                run_id,
                publish_event,
                "thinking",
                "Waiting for model…",
                step_counter,
                room=(context.last_state or {}).get("room"),
            )

            prev_msg_count = len(messages)
            round_emitted: set[str] = set()

            async def emit_thought(text: str) -> None:
                cleaned = text.strip()
                if cleaned and cleaned in round_emitted:
                    return
                if cleaned:
                    round_emitted.add(cleaned)
                room = (context.last_state or {}).get("room")
                await emit_custom_event(
                    db,
                    run_id,
                    publish_event,
                    "thought",
                    cleaned,
                    step_counter,
                    room=room if isinstance(room, str) else None,
                )

            stuck_detected = False
            try:
                result, stuck_detected = await invoke_agent_with_thoughts(
                    executor,
                    messages,
                    config={"recursion_limit": min(max_steps * 2, 150)},
                    idle_timeout=idle_timeout_sec,
                    stop_event=stop_event,
                    emit_thought=emit_thought,
                    command_count_fn=lambda: context.command_count,
                    stuck_idle_sec=stuck_idle_sec,
                    is_paused_fn=lambda: is_run_paused(run_id),
                )
            except RuntimeError as exc:
                raise RuntimeError(f"LLM round {round_idx + 1}: {exc}") from exc
            messages = result["messages"]

            for msg in messages[prev_msg_count:]:
                if not isinstance(msg, AIMessage):
                    continue
                thought = thought_from_message(msg)
                if thought:
                    await emit_thought(thought)

            if context.success:
                break

            last = context.last_state or {}
            if stuck_detected:
                await emit_custom_event(
                    db,
                    run_id,
                    publish_event,
                    "system",
                    (
                        "Agent stuck in text-only mode — injecting tool nudge "
                        f"({context.command_count} commands so far)"
                    ),
                    step_counter,
                    room=last.get("room") if isinstance(last.get("room"), str) else None,
                )
                if context.human_assists_remaining() > 0:
                    tool_nudge = (
                        "You stopped calling tools and only wrote text. "
                        "Do NOT apologize or explain. Call send_command OR ask_human NOW. "
                    )
                else:
                    tool_nudge = (
                        "You stopped calling send_command and only wrote text. "
                        "Do NOT apologize or explain. Call send_command NOW with your next game action. "
                    )
                messages.append(
                    HumanMessage(
                        content=(
                            tool_nudge
                            + f"Current room: {last.get('room', 'unknown')}. "
                            f"Inventory: {last.get('inventory', [])}. "
                            f"Visible items: {last.get('visible_items', [])}."
                        )
                    )
                )
                continue

            messages.append(
                HumanMessage(
                    content=build_round_continuation_nudge(
                        commands_used=context.command_count,
                        max_steps=max_steps,
                        human_assists_remaining=context.human_assists_remaining(),
                        ending=last.get("ending"),
                        room=str(last.get("room", "unknown")),
                        inventory=list(last.get("inventory", [])),
                    )
                )
            )

        if stop_event.is_set():
            raise asyncio.CancelledError()

        success = context.success
        run.success = success
        run.status = "completed" if success else "failed"
        run.steps_count = step_counter[0]
        run.human_assists_used = context.human_assists_used
        run.error_message = None
        run.finished_at = utc_now()
        db.commit()

        steps = [
            {
                "type": s.type,
                "content": s.content,
                "room": s.room,
            }
            for s in db.query(StepRecord).filter_by(run_id=run_id).order_by(StepRecord.step_number)
        ]
        summary, memory_source = await memory_agent.store_run_summary(
            run_id,
            steps,
            success,
            explorer_model,
            memory_session_id,
            last_state=context.last_state,
            commands_used=context.command_count,
            max_commands=max_steps,
        )
        await emit_custom_event(
            db,
            run_id,
            publish_event,
            "memory_stored",
            summary,
            step_counter,
            extra={"memory_source": memory_source},
        )

        final_messages = result.get("messages", [])
        final_answer = message_text(final_messages[-1]) if final_messages else ""

        await _publish(
            run_id,
            {
                "type": "run_complete",
                "run_id": run_id,
                "success": success,
                "steps": step_counter[0],
                "commands": context.command_count,
                "final_answer": final_answer,
                "memory_session_id": memory_session_id,
            },
        )
    except asyncio.CancelledError:
        run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
        stopped_session_id = (
            (run.memory_session_id or run.id) if run else memory_session_id
        )
        if run:
            run.status = "stopped"
            run.finished_at = utc_now()
            run.steps_count = step_counter[0]
            db.commit()
        await _publish(
            run_id,
            {
                "type": "run_failed",
                "run_id": run_id,
                "reason": "stopped",
                "memory_session_id": stopped_session_id,
            },
        )
    except Exception as exc:
        run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
        failed_session_id = (
            (run.memory_session_id or run.id) if run else memory_session_id
        )
        already_completed = bool(run and run.status == "completed" and run.success)
        if run:
            if not already_completed:
                run.status = "failed"
                run.error_message = str(exc)
                if not run.finished_at:
                    run.finished_at = utc_now()
                run.steps_count = step_counter[0]
            else:
                logging.getLogger(__name__).warning(
                    "Post-success cleanup failed for run %s: %s",
                    run_id,
                    exc,
                )
            db.commit()
        if already_completed and run:
            await _publish(
                run_id,
                {
                    "type": "run_complete",
                    "run_id": run_id,
                    "success": True,
                    "steps": run.steps_count,
                    "commands": context.command_count,
                    "final_answer": "",
                    "memory_session_id": failed_session_id,
                },
            )
        else:
            await _publish(
                run_id,
                {
                    "type": "run_failed",
                    "run_id": run_id,
                    "reason": str(exc),
                    "memory_session_id": failed_session_id,
                },
            )
    finally:
        cleanup_run(run_id)
        if game_client is not None:
            await game_client.close()
        db.close()


def create_run_record(
    db: Session,
    explorer_model: str,
    memory_model: str,
    memory_session_id: str | None = None,
    max_steps: int | None = None,
    max_human_assists: int = 0,
    continued_from_run_id: str | None = None,
    is_fresh_attempt: bool = False,
) -> RunRecord:
    """Insert a new ``runs`` row with status ``running``."""
    run_id = str(uuid4())
    run = RunRecord(
        id=run_id,
        explorer_model=explorer_model,
        memory_model=memory_model,
        status="running",
        memory_session_id=memory_session_id or run_id,
        continued_from_run_id=continued_from_run_id,
        is_fresh_attempt=is_fresh_attempt,
        max_steps=max_steps,
        max_human_assists=max(0, min(3, max_human_assists)),
        human_assists_used=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
