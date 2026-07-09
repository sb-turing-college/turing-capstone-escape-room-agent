"""Build run-end memory documents from agent reflections or LLM fallback."""

from __future__ import annotations

from typing import Any

REFLECTION_MIN_CHARS = 80
FOOTER_HEADER = "Ground truth (game state at run end):"
PRIOR_ATTEMPT_NOTE_PREFIX = "[Prior attempt ended at room '"


def extract_final_reflection(steps: list[dict[str, Any]]) -> str | None:
    """Return the last non-empty thought step content, if any."""
    for step in reversed(steps):
        if step.get("type") != "thought":
            continue
        content = str(step.get("content") or "").strip()
        if content:
            return content
    return None


def reflection_usable(text: str | None, *, min_chars: int = REFLECTION_MIN_CHARS) -> bool:
    """True when the agent produced a substantive closing reflection."""
    if not text:
        return False
    cleaned = text.strip()
    if len(cleaned) < min_chars:
        return False
    lowered = cleaned.lower()
    if lowered.startswith("llm round ") and "waiting for model" in lowered:
        return False
    return True


def format_state_footer(
    last_state: dict[str, Any] | None,
    *,
    success: bool,
    commands_used: int,
    max_commands: int,
) -> str:
    """Strict key-value footer the explorer should treat as factual ground truth."""
    state = last_state or {}
    room = state.get("room") or "unknown"
    inventory = state.get("inventory") or []
    if isinstance(inventory, list):
        inventory_text = ", ".join(str(item) for item in inventory) if inventory else "empty"
    else:
        inventory_text = str(inventory)
    ending = state.get("ending")
    ending_text = str(ending) if ending else "none"

    lines = [
        "---",
        FOOTER_HEADER,
        f"success: {str(success).lower()}",
        f"room: {room}",
        f"inventory: {inventory_text}",
        f"commands_used: {commands_used}/{max_commands}",
        f"ending: {ending_text}",
    ]
    visible = state.get("visible_items")
    if isinstance(visible, list) and visible:
        lines.append(f"visible_items: {', '.join(str(item) for item in visible)}")
    return "\n".join(lines)


def compose_run_memory_document(reflection: str, footer: str) -> str:
    """Join agent reflection with the factual footer."""
    parts = [reflection.strip()]
    footer = footer.strip()
    if footer:
        parts.extend(["", footer])
    return "\n".join(parts)


def format_prior_attempt_note(
    *,
    room: str,
    ending: str | None,
    commands_used: int,
    max_commands: int | None = None,
) -> str:
    """One-line historical metric replacing the end-state footer on fresh retries."""
    ending_text = str(ending) if ending else "none"
    if max_commands is not None:
        commands_part = f"{commands_used}/{max_commands}"
    else:
        commands_part = str(commands_used)
    return (
        f"{PRIOR_ATTEMPT_NOTE_PREFIX}{room}' with ending '{ending_text}' "
        f"after {commands_part} commands. Simulation is now reset.]"
    )


def _parse_state_footer_block(footer_block: str) -> tuple[str, str | None, int, int | None]:
    room = "unknown"
    ending: str | None = "none"
    commands_used = 0
    max_commands: int | None = None
    for line in footer_block.splitlines():
        stripped = line.strip()
        if stripped.startswith("room:"):
            room = stripped.split(":", 1)[1].strip() or room
        elif stripped.startswith("ending:"):
            raw = stripped.split(":", 1)[1].strip()
            ending = None if raw.lower() == "none" else raw
        elif stripped.startswith("commands_used:"):
            raw = stripped.split(":", 1)[1].strip()
            if "/" in raw:
                used_text, max_text = raw.split("/", 1)
                commands_used = int(used_text.strip())
                max_commands = int(max_text.strip())
            else:
                commands_used = int(raw)
    return room, ending, commands_used, max_commands


def replace_state_footer_for_fresh_attempt(document: str) -> str:
    """Replace ground-truth footer with a historical one-liner for retry runs."""
    if FOOTER_HEADER not in document:
        return document

    reflection_part, footer_block = document.split(FOOTER_HEADER, 1)
    room, ending, commands_used, max_commands = _parse_state_footer_block(footer_block)
    note = format_prior_attempt_note(
        room=room,
        ending=ending,
        commands_used=commands_used,
        max_commands=max_commands,
    )
    reflection = reflection_part.rstrip()
    if reflection:
        return f"{reflection}\n\n{note}"
    return note
