"""Verb parser for the text adventure (action verbs + look + inventory + read)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .content import DIRECTION_ALIASES
from .game_constants import unknown_verb_message

Verb = Literal[
    "examine", "take", "use", "open", "go", "look", "inventory", "read",
    "touch", "pull", "speak", "unknown",
]

UNKNOWN_VERB_MSG = unknown_verb_message()

# Verbs that work both with and without a target (e.g. "touch" alone prompts
# for a target, "touch painting" resolves it directly).
_OPTIONAL_TARGET_VERBS: tuple[Verb, ...] = ("touch", "pull", "speak", "read")

VERB_PATTERNS: list[tuple[Verb, re.Pattern[str]]] = [
    ("inventory", re.compile(r"^(inventory|inv|i)$", re.I)),
    ("look", re.compile(r"^(look around)$", re.I)),
    ("go", re.compile(
        r"^(go|walk|move)\s+("
        r"north-west|north-east|south-west|south-east|north|south|east|west|"
        r"northwest|northeast|southwest|southeast|nw|ne|sw|se|n|s|e|w"
        r")$",
        re.I,
    )),
    ("go", re.compile(r"^(go|walk|move)\s+(.+)$", re.I)),
    ("use", re.compile(r"^(use|combine)\s+(.+?)\s+(with|on)\s+(.+)$", re.I)),
    ("use", re.compile(r"^(use|combine)\s+(.+?)\s+(\d[\d\s]*)$", re.I)),
    ("use", re.compile(r"^(use|combine)\s+(.+)$", re.I)),
    ("open", re.compile(r"^(open|unlock)\s+(.+?)\s+(with)\s+(.+)$", re.I)),
    ("open", re.compile(r"^(open|unlock)\s+(.+)$", re.I)),
    ("examine", re.compile(r"^(examine|inspect|look at|x)\s+(.+)$", re.I)),
    ("read", re.compile(r"^(read)\s+(.+)$", re.I)),
    ("read", re.compile(r"^(read)$", re.I)),
    ("take", re.compile(r"^(take|get|grab|pick up)\s+(.+)$", re.I)),
    ("touch", re.compile(r"^(touch)\s+(.+)$", re.I)),
    ("touch", re.compile(r"^(touch)$", re.I)),
    ("pull", re.compile(r"^(pull)\s+(.+)$", re.I)),
    ("pull", re.compile(r"^(pull)$", re.I)),
    ("speak", re.compile(r"^(speak)\s+(?:to\s+)?(.+)$", re.I)),
    ("speak", re.compile(r"^(speak)$", re.I)),
]


@dataclass
class ParsedCommand:
    verb: Verb
    target: str | None = None
    secondary: str | None = None
    direction: str | None = None


def parse_command(raw: str) -> ParsedCommand:
    """Parse a raw player command into verb, targets, and direction."""
    text = raw.strip()
    if not text:
        return ParsedCommand(verb="unknown")

    for verb, pattern in VERB_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue

        if verb in ("inventory", "look"):
            return ParsedCommand(verb=verb)

        if verb == "go":
            dest = match.group(2).strip()
            key = dest.lower()
            if key in DIRECTION_ALIASES:
                return ParsedCommand(verb="go", direction=key)
            return ParsedCommand(verb="go", target=dest)

        if verb in ("use", "open"):
            if match.lastindex == 4:
                return ParsedCommand(
                    verb=verb,
                    target=match.group(2).strip(),
                    secondary=match.group(4).strip(),
                )
            if verb == "use" and match.lastindex == 3:
                digits = match.group(3).strip().replace(" ", "")
                if digits.isdigit():
                    return ParsedCommand(
                        verb=verb,
                        target=match.group(2).strip(),
                        secondary=match.group(3).strip(),
                    )
            return ParsedCommand(verb=verb, target=match.group(2).strip())

        if verb in ("examine", "take"):
            return ParsedCommand(verb=verb, target=match.group(2).strip())

        if verb in _OPTIONAL_TARGET_VERBS:
            has_target = match.lastindex is not None and match.lastindex >= 2
            return ParsedCommand(verb=verb, target=match.group(2).strip() if has_target else None)

    return ParsedCommand(verb="unknown")
