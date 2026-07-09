"""Game-wide constants, verb list, and direction aliases."""

from __future__ import annotations

from typing import Dict

CODE = "617482"
FAVORITE_A = 482
FAVORITE_B = 617
LOCKED_MSG = "It seems to be locked."
SAFE_CODE_HINT = (
    'A safe with a 6-digit number combination from 0-9. '
    'Type "use safe number" to enter a combination.'
)
SAFE_FAKE_NUMBER_MSG = "Nice try. Enter a real number."


def is_safe_literal_number_attempt(
    target_raw: str,
    sec_raw: str | None,
    resolved_target: str | None,
) -> bool:
    """True when the player typed the literal word ``number`` instead of digits."""
    target = target_raw.strip().lower()
    secondary = (sec_raw or "").strip().lower()
    if target in ("safe number", "safe with number"):
        return True
    return secondary == "number" and resolved_target == "safe"


from .game_constants import available_verbs

VERBS = available_verbs()


DIRECTION_ALIASES: Dict[str, str] = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
    "north-west": "north-west", "northwest": "north-west", "nw": "north-west",
    "north-east": "north-east", "northeast": "north-east", "ne": "north-east",
    "south-west": "south-west", "southwest": "south-west", "sw": "south-west",
    "south-east": "south-east", "southeast": "south-east", "se": "south-east",
    "down": "down", "d": "down",
}
