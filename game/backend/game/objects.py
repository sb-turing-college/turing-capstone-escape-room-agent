"""Game objects and alias resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .verbs import FAVORITE_A, FAVORITE_B

@dataclass(frozen=True)
class GameObject:
    """A thing in the game.

    takeable          – can be picked up into the inventory
    scenery           – fixed part of the room (door, grate, painting)
    flavor            – only examinable, does NOT appear in visible_items
    visible_when_flag – only visible while this flag is True
    describe_default  – default description
    describe_overrides– (flag, text): first matching override wins
    read_requires_holding – if True, `examine` always shows describe_before_taken
                            (physical description only). `read` reveals
                            describe_default (and examine_image) once the item
                            is held; before that it asks the player to take it.
    room_mention           – exact text fragment inside the owning room's
                              `description` that names this item. Once the
                              item has been taken from that room, the engine
                              strips this fragment so `look around` stops
                              mentioning objects that are no longer there.
    room_mention_reveal_after – if set, `room_mention` is NOT in the base room
                              description; it is appended once the named item
                              has been taken in this room and this item has not.
    """

    id: str
    aliases: Tuple[str, ...]
    label: str
    takeable: bool = False
    scenery: bool = False
    flavor: bool = False
    visible_when_flag: str | None = None
    hidden_until_taken: str | None = None  # hidden until this item was taken in the room
    take_text: str = ""
    describe_default: str = ""
    describe_overrides: Tuple[Tuple[str, str], ...] = ()
    examine_image: str | None = None  # optional image path shown alongside examine (Phase 3c)
    read_requires_holding: bool = False
    describe_before_taken: str = ""
    room_mention: str | None = None
    room_mention_reveal_after: str | None = None
    # Substrings in the owning room's `description` swapped when flags change
    # (e.g. door open). Keeps room prose fixed; state lives on the object.
    room_state_replaces: Tuple[Tuple[str, str, str], ...] = ()


_MEMO_TEXT = (
    "The note reads: \"I told you many times, DON'T TOUCH THAT PAINTING IN MY OFFICE! \n"
    "Next time you are fired.\n"
    "- Lord Daedaron\""
)

OBJECTS: Dict[str, GameObject] = {
    # --- Library ---
    "brass_key": GameObject(
        id="brass_key",
        aliases=("brass key", "brass_key", "key"),
        label="Brass Key",
        takeable=True,
        take_text="You take the brass key.",
        describe_default="A solid key. Where might it fit?",
        room_mention="a gleaming brass key and ",
    ),
    "lockbox": GameObject(
        id="lockbox",
        aliases=("lockbox", "box", "casket"),
        label="Lockbox",
        scenery=True,
        describe_default="A wooden lockbox. Locked.",
        describe_overrides=(
            ("lockbox_open", "The lockbox is open. A note lies inside."),
            ("lockbox_unlocked", "The lockbox is unlocked."),
        ),
    ),
    "note_code": GameObject(
        id="note_code",
        aliases=("note_code", "code", "paper"),
        label="Note",
        takeable=True,
        visible_when_flag="lockbox_open",
        take_text="You take the note.",
        describe_default=(
            f"The note reads: \"My favorite numbers: {FAVORITE_A} and {FAVORITE_B}. "
            "But I don't know which I like more.\""
        ),
        read_requires_holding=True,
        describe_before_taken="A note with scribbled writing.",
    ),
    "door": GameObject(
        id="door",
        aliases=("door", "oak door"),
        label="Oak Door",
        scenery=True,
        describe_default="A heavy oak door. Locked.",
        describe_overrides=(
            ("door_open", "The door stands open. A parlor lies beyond."),
            ("door_unlocked", "The door is unlocked."),
        ),
        room_state_replaces=(
            (
                "door_open",
                "A heavy oak door leads south.",
                "A heavy oak door leads south – it stands open.",
            ),
        ),
    ),
    "desk": GameObject(
        id="desk",
        aliases=("desk", "writing desk"),
        label="Desk",
        flavor=True,
        describe_default="An old oak writing desk. Has likely seen better days.",
    ),
    "bookshelf": GameObject(
        id="bookshelf",
        aliases=("bookshelf", "bookshelves", "shelf", "shelves", "books"),
        label="Bookshelf",
        flavor=True,
        describe_default="Tall shelves full of dusty books. Nothing remarkable.",
    ),
    # --- Parlor ---
    "note_memo": GameObject(
        id="note_memo",
        aliases=("note_memo", "memo"),
        label="Memo",
        takeable=True,
        take_text="As you take the memo, a small key is being revealed.",
        describe_default=_MEMO_TEXT,
        read_requires_holding=True,
        describe_before_taken="A crumpled memo.",
        room_mention="A crumpled memo lies on the mantelpiece. ",
    ),
    "small_key": GameObject(
        id="small_key",
        aliases=("small_key", "small key", "little key"),
        label="Small Key",
        takeable=True,
        hidden_until_taken="note_memo",
        take_text="You take the small key.",
        describe_default="A small key.",
        room_mention="A small key glints on the mantelpiece. ",
        room_mention_reveal_after="note_memo",
    ),
    "rope": GameObject(
        id="rope",
        aliases=("rope",),
        label="Rope",
        takeable=True,
        take_text="You take the rope.",
        describe_default="A long, sturdy rope.",
        room_mention="A rope lies on the floor. ",
    ),
    "hook": GameObject(
        id="hook",
        aliases=("hook",),
        label="Hook",
        takeable=True,
        take_text="With some effort you pry the hook from the wall.",
        describe_default="A rusty iron hook.",
        room_mention="A rusty hook is fixed in the wall. ",
    ),
    "chainsaw": GameObject(
        id="chainsaw",
        aliases=("chainsaw", "saw"),
        label="Chainsaw",
        takeable=True,
        take_text="You take the bulky, heavy chainsaw.",
        describe_default="A heavy chainsaw. The tank is completely empty.",
        room_mention="A chainsaw stands in the corner. ",
    ),
    "grate": GameObject(
        id="grate",
        aliases=("grate", "iron grate", "bars", "gate"),
        label="Iron Grate",
        scenery=True,
        describe_default="A massive iron grate up to the ceiling. No way through.",
        describe_overrides=(
            (
                "grate_open",
                "A massive iron grate up to the ceiling. A grappling hook is now "
                "fixed at the top, its rope hanging down within reach.",
            ),
        ),
    ),
    # Decorative fixture left behind once the grate has been opened (Phase
    # 5b): the grappling_hook item is consumed and reappears here as a
    # permanent scene fixture instead of instantly teleporting the player.
    "hook_on_grate": GameObject(
        id="hook_on_grate",
        aliases=("hook_on_grate", "hanging hook", "fixed hook"),
        label="Hook on the Grate",
        scenery=True,
        visible_when_flag="grate_open",
        describe_default=(
            "The grappling hook is lodged firmly over the top of the grate, "
            "its rope dangling down into the gap below."
        ),
    ),
    "fireplace": GameObject(
        id="fireplace",
        aliases=("fireplace", "mantel", "mantelpiece", "chimney"),
        label="Fireplace",
        flavor=True,
        describe_default="A large, cold fireplace. No traces of ashes... strange.",
        describe_overrides=(
            (
                "chimney_ladder_visible",
                "The fireplace now hides a wooden ladder leading down into a "
                "eerily glowing pit.",
            ),
        ),
    ),
    # Invisible pseudo-object: only resolvable as the target of "speak fiend"
    # (Phase 4a). Never listed in any room's `objects`, so it never appears
    # in visible_items / can never be examined - purely an interaction key.
    "fiend": GameObject(
        id="fiend",
        aliases=("fiend",),
        label="Fiend",
        flavor=True,
    ),
    "unearthly_ladder": GameObject(
        id="unearthly_ladder",
        aliases=("unearthly_ladder", "ladder", "unearthly ladder"),
        label="Unearthly Ladder",
        visible_when_flag="chimney_ladder_visible",
        describe_default=(
            "A rough wooden ladder now leads down into the fireplace, into a "
            "shaft that should not exist. An eerie red glow rises from below. No, you don't want to go down there."
        ),
    ),
    "window": GameObject(
        id="window",
        aliases=("window", "windows"),
        label="Window",
        flavor=True,
        describe_default="Tall windows. Night lies beyond.",
    ),
    # --- derived object ---
    "grappling_hook": GameObject(
        id="grappling_hook",
        aliases=("grappling_hook", "grappling hook", "grapple"),
        label="Grappling Hook",
        takeable=True,
        describe_default="A rope tied to a hook – could be useful.",
    ),
    # --- Lord's Office ---
    "painting": GameObject(
        id="painting",
        aliases=("painting", "picture", "oil painting"),
        label="Painting",
        scenery=True,
        describe_default=(
            "An oil painting. A castle on the shore of a lake. It hangs oddly far "
            "from the wall."
        ),
        describe_overrides=(("painting_open", "A safe behind the painting... of course!"),),
    ),
    "safe": GameObject(
        id="safe",
        aliases=("safe", "vault", "combination lock"),
        label="Safe",
        scenery=True,
        visible_when_flag="painting_open",
        describe_default="A massive steel safe in the wall. A six-digit combination lock – six wheels, 0–9.",
        describe_overrides=(
            ("safe_open", "The safe stands open. Inside lies a mysterious old book atop a pile of coins and pearls. You feel a chill run down your spine."),
            ("safe_unlocked", "The safe is unlocked."),
        ),
    ),
    "floor": GameObject(
        id="floor",
        aliases=("floor", "dust", "ground"),
        label="Floor",
        flavor=True,
        describe_default="Thick dust covers the floor. Nothing else lies here.",
    ),
    "secret_book": GameObject(
        id="secret_book",
        aliases=("secret_book", "book", "old book", "diary"),
        label="Old Book",
        takeable=True,
        visible_when_flag="safe_open",
        take_text="You take the old book from the safe.",
        describe_default=(
            "You flip through the pages with mysterious symbols and unreadable "
            "gibberish when a certain page catches your notice: a strangely "
            "familiar chimney with hellish flames and a note beside it: "
            '"Speak Fiend and you may enter"'
        ),
        examine_image="/assets/examine/secret_book_open.png",
        read_requires_holding=True,
        describe_before_taken=(
            "A mysterious old book. You have a bad feeling about that."
        ),
    ),
}

# ---------------------------------------------------------------------------
# Derived lookup table: alias -> object id
# (the ambiguous bare word "note" is resolved contextually in the engine)
# ---------------------------------------------------------------------------
ALIAS_TO_ID: Dict[str, str] = {}
for _obj in OBJECTS.values():
    for _alias in _obj.aliases:
        ALIAS_TO_ID[_alias.lower()] = _obj.id

# Only the bare word "note" is ambiguous (memo vs. code note);
# "memo" -> memo, "code"/"paper" -> code note are unambiguous.
AMBIGUOUS_NOTE = {"note"}
