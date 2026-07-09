"""Load synced game display constants (source: capstone-game/shared/)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent / "shared" / "game_constants.json"


@lru_cache(maxsize=1)
def load_game_constants() -> dict[str, Any]:
    """Load synced ``game_constants.json`` (source: capstone-game/shared/)."""
    return json.loads(_PATH.read_text(encoding="utf-8"))


def room_label(room_id: str) -> str:
    """Return the display label for a room id, or the id itself if unknown."""
    labels: dict[str, str] = load_game_constants()["room_labels"]
    return labels.get(room_id, room_id)


def _commands() -> dict[str, Any]:
    return load_game_constants()["commands"]


def available_verbs() -> list[str]:
    return list(_commands()["verbs"])


def syntax_patterns() -> list[str]:
    return list(_commands()["syntax_patterns"])


def format_available_verbs_line() -> str:
    return ", ".join(available_verbs())


def format_syntax_patterns_line() -> str:
    return ", ".join(f'"{pattern}"' for pattern in syntax_patterns())


def send_command_tool_description() -> str:
    return (
        "Send one English text command to the game. "
        f"Available verbs: {format_available_verbs_line()}. "
        f"Syntax patterns: {format_syntax_patterns_line()}. "
        "Replace X/Y with actual item names you've discovered in the game — "
        "never invent solutions, only use what the game has shown you."
    )
