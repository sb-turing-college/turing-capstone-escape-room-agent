"""Injected loop nudges for explorer runs (low budget, etc.)."""

from __future__ import annotations


def low_budget_command_threshold(max_steps: int) -> int:
    """Rough 25% of send_command budget — matches HUMAN_ASSIST_PROMPT guidance."""
    return max(1, max_steps // 4)


def build_fresh_attempt_nudge() -> str:
    return (
        "System: This is a new attempt. The simulation has been reset — your inventory "
        "is empty and all doors are locked again. Use your memory of previous runs to "
        "solve puzzles faster with fewer send_command steps, but repeat every physical "
        "action in the game."
    )


def build_low_budget_ask_human_nudge(
    commands_remaining: int,
    human_assists_remaining: int,
) -> str:
    return (
        f"Warning: You only have {commands_remaining} send_command(s) remaining. "
        "If you are stuck or do not have a clear solution, use ask_human NOW "
        f"({human_assists_remaining} assist(s) left) before your budget runs out."
    )


def build_continue_start_nudge(
    *,
    max_steps: int,
    human_assists_remaining: int,
) -> str:
    """One-shot budget reset injected before the first LLM round on Continue Run."""
    return (
        f"Run status: commands_used=0/{max_steps}, "
        f"human_assists_remaining={human_assists_remaining} — "
        "fresh command budget for this segment."
    )


def build_round_continuation_nudge(
    *,
    commands_used: int,
    max_steps: int,
    human_assists_remaining: int,
    ending: object,
    room: str,
    inventory: list,
) -> str:
    """Post-round status the model sees before its next tool decision."""
    status = (
        f"Run status: commands_used={commands_used}/{max_steps}, "
        f"human_assists_remaining={human_assists_remaining}.\n"
    )
    if human_assists_remaining > 0:
        action = "Continue with send_command or ask_human if appropriate."
    else:
        action = "Continue with send_command."
    return (
        status
        + "You have NOT finished the demo yet — the last game response had "
        + f"ending={ending!r}. Current room: {room}. "
        + f"Inventory: {inventory}. "
        + f"{action} Keep exploring, reading, and experimenting until you discover "
        + "the path to the ending yourself."
    )
