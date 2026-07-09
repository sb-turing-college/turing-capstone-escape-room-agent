"""Interaction rules and red herrings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .verbs import LOCKED_MSG, SAFE_CODE_HINT

@dataclass(frozen=True)
class Effect:
    """State changes applied when an interaction succeeds."""

    set_flags: Tuple[Tuple[str, bool], ...] = ()
    add_items: Tuple[str, ...] = ()
    remove_items: Tuple[str, ...] = ()
    move_to_room: str | None = None
    solved: bool = False


@dataclass(frozen=True)
class Interaction:
    """A rule for puzzle verbs (`use`, `open`, `examine`, …).

    Matching: verb in verbs AND objects == resolved object set AND room matches,
    AND flag preconditions are satisfied. `code_for` marks code locks (the
    secondary argument is then a number).
    """

    verbs: frozenset[str]
    objects: frozenset[str]
    room: str
    needs_inventory: Tuple[str, ...] = ()
    needs_flags_true: Tuple[str, ...] = ()
    needs_flags_false: Tuple[str, ...] = ()
    already_flag: str | None = None
    already_text: str = ""
    blocked_text: str = "That doesn't work here."
    success_text: str = ""
    wrong_code_text: str = ""
    code_for: str | None = None
    effect: Effect = field(default_factory=Effect)


_USE = frozenset({"use"})

INTERACTIONS: List[Interaction] = [
    # --- Library: unlock with use, open physically ---
    Interaction(
        verbs=_USE,
        objects=frozenset({"lockbox", "brass_key"}),
        room="library",
        success_text="The brass key does not fit the lockbox's small lock.",
    ),
    Interaction(
        verbs=_USE,
        objects=frozenset({"lockbox", "small_key"}),
        room="library",
        needs_inventory=("small_key",),
        already_flag="lockbox_unlocked",
        already_text="The lockbox is already unlocked.",
        success_text="The key turns. You hear a faint click – the lockbox is unlocked, but still closed.",
        effect=Effect(set_flags=(("lockbox_unlocked", True),)),
    ),
    Interaction(
        verbs=frozenset({"open"}),
        objects=frozenset({"lockbox"}),
        room="library",
        needs_flags_true=("lockbox_unlocked",),
        blocked_text=LOCKED_MSG,
        already_flag="lockbox_open",
        already_text="The lockbox is already open.",
        success_text="You lift the lid. Inside lies a note.",
        effect=Effect(set_flags=(("lockbox_open", True),)),
    ),
    Interaction(
        verbs=_USE,
        objects=frozenset({"door", "brass_key"}),
        room="library",
        needs_inventory=("brass_key",),
        already_flag="door_unlocked",
        already_text="The door is already unlocked.",
        success_text="The key fits in the lock. The door is unlocked, but still closed.",
        effect=Effect(set_flags=(("door_unlocked", True),)),
    ),
    Interaction(
        verbs=frozenset({"open"}),
        objects=frozenset({"door"}),
        room="library",
        needs_flags_true=("door_unlocked",),
        blocked_text=LOCKED_MSG,
        already_flag="door_open",
        already_text="The door is already open.",
        success_text="The oak door swings open.",
        effect=Effect(set_flags=(("door_open", True),)),
    ),
    # --- Parlor ---
    Interaction(
        verbs=_USE,
        objects=frozenset({"rope", "hook"}),
        room="parlor",
        needs_inventory=("rope", "hook"),
        success_text="You tie the rope to the hook. You are holding a grappling hook.",
        effect=Effect(add_items=("grappling_hook",), remove_items=("rope", "hook")),
    ),
    Interaction(
        verbs=_USE,
        objects=frozenset({"grappling_hook", "grate"}),
        room="parlor",
        needs_inventory=("grappling_hook",),
        already_flag="grate_open",
        already_text="The grappling hook is already fixed to the top of the grate.",
        success_text=(
            "You throw the grappling hook up and over the top of the grate. "
            "It catches fast – the rope now hangs down within reach, and the "
            "way through lies open."
        ),
        effect=Effect(set_flags=(("grate_open", True),), remove_items=("grappling_hook",)),
    ),
    Interaction(
        verbs=frozenset({"open"}),
        objects=frozenset({"grate"}),
        room="parlor",
        success_text=LOCKED_MSG,
    ),
    Interaction(
        # Works "at any time" per spec - no flag requirement. The player only
        # knows the phrase once they've read the secret book, but nothing in
        # the engine gates it on `is_solved`.
        verbs=frozenset({"speak"}),
        objects=frozenset({"fiend"}),
        room="parlor",
        already_flag="chimney_ladder_visible",
        already_text="The ladder is already there, waiting in the fireplace.",
        success_text=(
            "The word echoes unnaturally. The fireplace's ashes stir, and a "
            "rough wooden ladder now leads down into a shaft that wasn't "
            "there a moment ago - a dull red glow rising from below."
        ),
        effect=Effect(set_flags=(("chimney_ladder_visible", True),)),
    ),
    # --- Lord's Office ---
    Interaction(
        # "pull painting" has the exact same effect as "open painting" - one
        # rule for both verbs instead of duplicating the logic.
        verbs=frozenset({"open", "pull"}),
        objects=frozenset({"painting"}),
        room="lords_office",
        already_flag="painting_open",
        already_text="The painting is already swung aside.",
        success_text=(
            "The painting swings out from the wall on a hidden hinge. "
            "**A steel safe is revealed!**"
        ),
        effect=Effect(set_flags=(("painting_open", True),)),
    ),
    Interaction(
        verbs=frozenset({"touch"}),
        objects=frozenset({"painting"}),
        room="lords_office",
        success_text="You touched the painting - it seemed to move briefly.",
    ),
    Interaction(
        verbs=frozenset({"examine"}),
        objects=frozenset({"safe"}),
        room="lords_office",
        needs_flags_true=("painting_open",),
        needs_flags_false=("safe_unlocked",),
        blocked_text="You don't see a safe here.",
        success_text=SAFE_CODE_HINT,
    ),
    Interaction(
        verbs=frozenset({"use"}),
        objects=frozenset({"safe"}),
        room="lords_office",
        needs_flags_true=("painting_open",),
        needs_flags_false=("safe_unlocked",),
        blocked_text="You don't see a safe here.",
        success_text=SAFE_CODE_HINT,
    ),
    Interaction(
        verbs=frozenset({"open"}),
        objects=frozenset({"safe"}),
        room="lords_office",
        needs_flags_true=("painting_open",),
        needs_flags_false=("safe_unlocked",),
        blocked_text="You don't see a safe here.",
        success_text=SAFE_CODE_HINT,
    ),
    Interaction(
        verbs=frozenset({"use"}),
        objects=frozenset({"safe"}),
        room="lords_office",
        code_for="safe",
        needs_flags_true=("painting_open",),
        already_flag="safe_unlocked",
        already_text="The safe is already unlocked.",
        blocked_text="You don't see a safe here.",
        success_text="Click. The combination is correct. The safe is unlocked, but still closed.",
        wrong_code_text="Wrong combination. The lock won't give.",
        effect=Effect(set_flags=(("safe_unlocked", True),)),
    ),
    Interaction(
        verbs=frozenset({"open"}),
        objects=frozenset({"safe"}),
        room="lords_office",
        needs_flags_true=("safe_unlocked",),
        blocked_text=LOCKED_MSG,
        success_text=(
            "You pull the handle. Inside the safe lies an old book, its cover "
            "worn with age. Something tells you it holds more of the house's secrets."
        ),
        # Opening the safe is a milestone, not the demo ending - `is_solved`
        # only becomes true once the chimney shaft ending is reached (see
        # GameSession's exit handling in engine.py). Confusing the two used
        # to make the API report `is_solved: true` mid-game.
        effect=Effect(set_flags=(("safe_open", True),)),
    ),
]


# Red herrings: object id -> response on `use` (dead end)
RED_HERRINGS: Dict[str, str] = {
    "chainsaw": "The chainsaw won't start. The tank is empty – you'd need fuel.",
}

