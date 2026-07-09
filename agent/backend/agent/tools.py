"""LangChain tools wrapping the game HTTP client."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.game_client import GameClient
from agent.run_registry import (
    PauseContext,
    format_agent_human_observation,
    format_human_hint_observation,
    is_run_paused,
    request_pause,
)
from game_constants import send_command_tool_description


class CommandInput(BaseModel):
    command: str = Field(description="Text command for the game, e.g. 'take brass key'")


class AskHumanInput(BaseModel):
    current_theory: str = Field(
        description=(
            "Your current understanding: room, inventory, what you tried, "
            "and what is unclear."
        ),
        min_length=40,
        max_length=1500,
    )
    question: str = Field(
        description=(
            "One specific question for the human observer. "
            "Do not ask for the full solution."
        ),
        min_length=10,
        max_length=500,
    )


class RunContext:
    """Shared per-run state for tools, callbacks, and runner."""

    def __init__(
        self,
        game_client: GameClient,
        on_game_update: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_tool_event: Callable[[str, str, str | None], Awaitable[None]] | None = None,
        on_command_blocked: Callable[[str, str], Awaitable[None]] | None = None,
        on_before_action: Callable[[], Awaitable[str | None]] | None = None,
        on_await_human_pause: Callable[
            [], Awaitable[tuple[str | None, PauseContext | None] | None]
        ]
        | None = None,
        on_human_assist_used: Callable[[int], Awaitable[None]] | None = None,
        moderate: Callable[[str], Awaitable[tuple[bool, str | None]]] | None = None,
        max_commands: int = 50,
        max_human_assists: int = 0,
        run_id: str | None = None,
    ) -> None:
        self.game_client = game_client
        self.on_game_update = on_game_update
        self.on_tool_event = on_tool_event
        self.on_command_blocked = on_command_blocked
        self.on_before_action = on_before_action
        self.on_await_human_pause = on_await_human_pause
        self.on_human_assist_used = on_human_assist_used
        self.moderate = moderate
        self._max_commands = max_commands
        self.max_human_assists = max_human_assists
        self.human_assists_used = 0
        self.run_id = run_id
        self.last_state: dict[str, Any] | None = None
        self.completed = False
        self.success = False
        self.command_count = 0

    def human_assists_remaining(self) -> int:
        return max(0, self.max_human_assists - self.human_assists_used)

    def _command_budget(self) -> dict[str, int]:
        return {
            "commands_used": self.command_count,
            "commands_remaining": max(0, self._max_commands - self.command_count),
        }

    def _json_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps({**payload, **self._command_budget()}, indent=2)

    async def _apply_state(self, state: dict[str, Any]) -> str:
        self.last_state = state
        if self.on_game_update:
            await self.on_game_update(state)
        if state.get("ending"):
            self.completed = True
            self.success = True
        return self._json_payload(state)

    async def _human_input_suffix(self) -> str:
        """Runs the pause checkpoint and formats any result as observation text."""
        if not self.on_before_action:
            return ""
        note = await self.on_before_action()
        return f"\n\n[{note}]" if note else ""

    async def send_command(self, command: str) -> str:
        human_note = await self._human_input_suffix()

        if self.command_count >= self._max_commands:
            message = "Step limit reached for this run."
            payload = {"error": message, "text": message, **self._command_budget()}
            return json.dumps(payload, indent=2) + human_note

        if self.moderate:
            allowed, reason = await self.moderate(command)
            if not allowed:
                message = reason or "Command blocked by moderation."
                if self.on_command_blocked:
                    await self.on_command_blocked(command, message)
                payload = {"error": message, "text": message, **self._command_budget()}
                return json.dumps(payload, indent=2) + human_note

        if self.on_tool_event:
            await self.on_tool_event("action", f"send_command: {command}", None)

        self.command_count += 1
        state = await self.game_client.send_command(command)
        payload = await self._apply_state(state)

        if self.on_tool_event:
            room = state.get("room") if isinstance(state.get("room"), str) else None
            await self.on_tool_event("observation", (payload + human_note)[:4000], room)

        return payload + human_note

    async def get_state(self) -> str:
        human_note = await self._human_input_suffix()
        state = await self.game_client.get_state()
        payload = await self._apply_state(state)
        return payload + human_note

    async def ask_human(self, current_theory: str, question: str) -> str:
        if self.max_human_assists <= 0:
            return json.dumps(
                {"error": "human_assist_disabled", "text": "ask_human is not available."},
                indent=2,
            )

        if self.human_assists_used >= self.max_human_assists:
            return json.dumps(
                {
                    "error": "human_assist_quota_exceeded",
                    "text": (
                        f"Human assist quota exhausted ({self.max_human_assists} "
                        "used). Continue without asking."
                    ),
                    "human_assists_used": self.human_assists_used,
                    "max_human_assists": self.max_human_assists,
                },
                indent=2,
            )

        if is_run_paused(self.run_id or ""):
            return json.dumps(
                {
                    "error": "run_already_paused",
                    "text": "Run is already paused — cannot ask_human now.",
                },
                indent=2,
            )

        if not request_pause(
            self.run_id or "",
            initiator="agent",
            agent_theory=current_theory.strip(),
            agent_question=question.strip(),
        ):
            return json.dumps(
                {
                    "error": "run_already_paused",
                    "text": "Run is already paused — cannot ask_human now.",
                },
                indent=2,
            )

        action_text = f"ask_human: {question.strip()}"
        if self.on_tool_event:
            room = (self.last_state or {}).get("room")
            room_str = room if isinstance(room, str) else None
            await self.on_tool_event("action", action_text, room_str)

        if not self.on_await_human_pause:
            return json.dumps(
                {"error": "pause_unavailable", "text": "Human pause is not configured."},
                indent=2,
            )

        resolution = await self.on_await_human_pause()
        if resolution is None:
            return json.dumps(
                {"error": "pause_failed", "text": "Failed to resolve human pause."},
                indent=2,
            )

        response, pause_ctx = resolution
        if pause_ctx is None or pause_ctx.initiator != "agent":
            return json.dumps(
                {"error": "pause_mismatch", "text": "Unexpected pause state."},
                indent=2,
            )

        self.human_assists_used += 1
        if self.on_human_assist_used:
            await self.on_human_assist_used(self.human_assists_used)
        observation = format_agent_human_observation(response)
        if self.on_tool_event:
            room = (self.last_state or {}).get("room")
            room_str = room if isinstance(room, str) else None
            await self.on_tool_event("observation", observation, room_str)

        return json.dumps(
            {
                "text": observation,
                **self._command_budget(),
                "human_assists_used": self.human_assists_used,
                "human_assists_remaining": self.human_assists_remaining(),
            },
            indent=2,
        )


def build_tools(context: RunContext) -> list[StructuredTool]:
    """Expose game tools and optional ask_human as LangChain structured tools."""

    async def send_command(command: str) -> str:
        """Send a text command to the haunted manor game and return the JSON response."""
        return await context.send_command(command)

    async def get_state() -> str:
        """Return the current game state as JSON without performing an action."""
        return await context.get_state()

    tools: list[StructuredTool] = [
        StructuredTool.from_function(
            coroutine=send_command,
            name="send_command",
            description=send_command_tool_description(),
            args_schema=CommandInput,
        ),
        StructuredTool.from_function(
            coroutine=get_state,
            name="get_state",
            description="Fetch current room, inventory, visible items, and exits without acting.",
        ),
    ]

    if context.max_human_assists > 0:

        async def ask_human(current_theory: str, question: str) -> str:
            """Pause the run and ask the human observer one focused question."""
            return await context.ask_human(current_theory, question)

        tools.append(
            StructuredTool.from_function(
                coroutine=ask_human,
                name="ask_human",
                description=(
                    "Pause and ask the human observer ONE question when you lack "
                    "information you cannot obtain via send_command/get_state. "
                    "Requires current_theory and a specific question. "
                    "Counts against your human assist quota."
                ),
                args_schema=AskHumanInput,
            )
        )

    return tools
