"""Room definitions and go-object exit map."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass(frozen=True)
class Exit:
    """One directional exit from a room, optionally gated by a flag."""

    target: str | None = None
    gate_flag: str | None = None
    locked_text: str = "There is no way through here."
    always_closed: bool = False
    # When set, taking this exit does NOT move the player to `target` - it
    # instead marks the response as a cinematic ending (Phase 4a). The
    # frontend detects this and plays the Chapter-1/demo-end sequence
    # instead of the normal room transition.
    ending: str | None = None
    # When True, this exit is omitted from `exits` entirely while still
    # locked - for secret exits the player has no way of knowing about yet
    # (Phase 5 follow-up: the chimney shaft must not show up as "Down:
    # locked" before `speak fiend` reveals the ladder).
    hidden_while_locked: bool = False


@dataclass(frozen=True)
class Room:
    """Static room definition: description, object ids, and exits."""

    description: str
    objects: Tuple[str, ...]
    exits: Dict[str, Exit] = field(default_factory=dict)
    description_replaces: Tuple[Tuple[str, str, str], ...] = ()  # (flag, old, new)
    description_appends: Tuple[Tuple[str, str], ...] = ()         # (flag, append)


ROOMS: Dict[str, Room] = {
    "library": Room(
        description=(
            "As you turn around, you realize the door to the manor has vanished! "
            "You are in a dusty library; tall bookshelves line the walls. "
            "A heavy oak door leads south. "
            "On the desk lies a gleaming brass key and an old lockbox."
        ),
        objects=("brass_key", "lockbox", "note_code", "door", "desk", "bookshelf"),
        exits={"south": Exit("parlor", "door_open", "The door is closed.")},
    ),
    "parlor": Room(
        description=(
            "A grand parlor with tall windows. A cold fireplace with a wide chimney "
            "rising into the dark dominates the room. "
            "A crumpled memo lies on the mantelpiece. "
            "A rope lies on the floor. "
            "A rusty hook is fixed in the wall. "
            "A chainsaw stands in the corner. "
            "To the south-west a heavy iron grate blocks the way."
        ),
        objects=(
            "note_memo",
            "small_key",
            "rope",
            "hook",
            "chainsaw",
            "grate",
            "hook_on_grate",
            "fireplace",
            "window",
            "unearthly_ladder",
        ),
        exits={
            "north": Exit("library"),
            "south-west": Exit(
                "lords_office",
                gate_flag="grate_open",
                locked_text="The iron grate blocks the way.",
            ),
            "down": Exit(
                gate_flag="chimney_ladder_visible",
                locked_text="There is nothing to go down here.",
                ending="chapter1",
                hidden_while_locked=True,
            ),
        },
        description_replaces=(
            (
                "grate_open",
                "To the south-west a heavy iron grate blocks the way.",
                "To the south-west, a grappling hook now hangs fixed atop the "
                "iron grate – the way through lies open.",
            ),
        ),
        description_appends=(
            (
                "chimney_ladder_visible",
                " A crude wooden ladder now leads down into the fireplace, "
                "into a shaft glowing faintly red.",
            ),
        ),
    ),
    "lords_office": Room(
        description=(
            "Lord's private office. Thick dust covers the floor. "
            "On the south wall hangs a large painting – a castle on the shore of a lake."
        ),
        objects=("painting", "safe", "floor", "secret_book"),
        exits={"north-east": Exit("parlor")},
        description_appends=(
            ("painting_open", " Behind the swung-aside painting a steel safe is visible."),
        ),
    ),
}



GO_OBJECT_EXITS: Dict[str, Dict[str, str]] = {
    "library": {"door": "south"},
    "parlor": {"unearthly_ladder": "down", "grate": "south-west", "hook_on_grate": "south-west"},
}

