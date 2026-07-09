"""Load shared game_constants.json (labels, map metadata, command vocabulary)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent.parent.parent / "shared" / "game_constants.json"


@lru_cache(maxsize=1)
def load_game_constants() -> dict[str, Any]:
    return json.loads(_PATH.read_text(encoding="utf-8"))


def _commands() -> dict[str, Any]:
    return load_game_constants()["commands"]


def available_verbs() -> list[str]:
    return list(_commands()["verbs"])


def syntax_patterns() -> list[str]:
    return list(_commands()["syntax_patterns"])


def unknown_verb_message() -> str:
    parts: list[str] = []
    for verb in available_verbs():
        parts.append(verb)
        if verb == "use":
            parts.append("use x with y")
    return f"Unknown command. Available verbs: {', '.join(parts)}."


def verb_default_fallback(verb: str) -> str:
    fallbacks: dict[str, str] = _commands().get("default_fallback", {})
    return fallbacks.get(verb, "This doesn't seem to work.")
