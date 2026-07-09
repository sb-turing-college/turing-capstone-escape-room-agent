"""Generic, data-driven adventure engine.

The engine evaluates content modules only (`rooms`, `objects`, `interactions`,
`verbs`; re-exported from `content.py`). It contains no hard-coded puzzles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .content import (
    ALIAS_TO_ID,
    AMBIGUOUS_NOTE,
    CODE,
    DIRECTION_ALIASES,
    GO_OBJECT_EXITS,
    INTERACTIONS,
    OBJECTS,
    RED_HERRINGS,
    ROOMS,
    SAFE_FAKE_NUMBER_MSG,
    VERBS,
    Effect,
    Interaction,
    is_safe_literal_number_attempt,
)
from .game_constants import verb_default_fallback
from .parser import UNKNOWN_VERB_MSG, ParsedCommand, parse_command
from .state import GameState

# In-memory session store (phase 1); optional SQLite persistence later
_sessions: Dict[str, "GameSession"] = {}


@dataclass
class GameStateResponse:
    """Wire format returned by the engine and REST API for one game turn."""

    text: str
    room: str
    visible_items: List[str]
    exits: Dict[str, str]
    inventory: List[str]
    is_solved: bool
    object_states: Dict[str, str] = field(default_factory=dict)
    available_verbs: List[str] = field(default_factory=lambda: list(VERBS))
    image: Optional[str] = None
    # Set when this turn triggers a cinematic ending (Phase 4a). The frontend
    # plays the Chapter-1/demo-end sequence instead of applying the response
    # normally; the room is intentionally left unchanged.
    ending: Optional[str] = None


class GameSession:
    """One in-memory play session: parses commands and mutates ``GameState``."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.state = GameState()

    # ------------------------------------------------------------------ helpers
    def _label(self, obj_id: str) -> str:
        obj = OBJECTS.get(obj_id)
        return obj.label if obj else obj_id

    def _resolve(self, raw: str | None) -> Optional[str]:
        if not raw:
            return None
        key = raw.strip().lower()
        if key in AMBIGUOUS_NOTE:
            return self._resolve_note()
        if key in ALIAS_TO_ID:
            return ALIAS_TO_ID[key]
        for variant in (key.replace("_", " "), key.replace(" ", "_")):
            if variant in ALIAS_TO_ID:
                return ALIAS_TO_ID[variant]
        return None

    def _resolve_note(self) -> Optional[str]:
        room = self.state.current_room
        taken = self.state.items_taken_in_room
        if room == "library" and self.state.flag("lockbox_open") and "note_code" not in taken("library"):
            return "note_code"
        if room == "parlor" and "note_memo" not in taken("parlor"):
            return "note_memo"
        if self.state.has_item("note_code"):
            return "note_code"
        if self.state.has_item("note_memo"):
            return "note_memo"
        return None

    def _object_visible_in_room(self, obj_id: str) -> bool:
        obj = OBJECTS.get(obj_id)
        if not obj or obj.flavor:
            return False
        if obj.visible_when_flag and not self.state.flag(obj.visible_when_flag):
            return False
        if obj.hidden_until_taken and obj.hidden_until_taken not in self.state.items_taken_in_room(
            self.state.current_room
        ):
            return False
        if obj.takeable and obj_id in self.state.items_taken_in_room(self.state.current_room):
            return False
        return True

    def _examine_text(self, obj_id: str) -> str:
        obj = OBJECTS[obj_id]
        if obj.read_requires_holding:
            return obj.describe_before_taken or self._describe(obj_id)
        return self._describe(obj_id)

    def _examine_image(self, obj_id: str) -> Optional[str]:
        obj = OBJECTS[obj_id]
        if obj.read_requires_holding:
            return None
        return obj.examine_image

    def _describe(self, obj_id: str) -> str:
        obj = OBJECTS[obj_id]
        for flag, text in obj.describe_overrides:
            if self.state.flag(flag):
                return text
        return obj.describe_default

    def _visible_items(self, room: str) -> List[str]:
        return [oid for oid in ROOMS[room].objects if self._object_visible_in_room(oid)]

    def _exits(self, room: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for direction, ex in ROOMS[room].exits.items():
            if ex.always_closed:
                out[direction] = "closed"
            elif ex.gate_flag is None:
                out[direction] = "open"
            elif ex.gate_flag == "door_open":
                if self.state.flag("door_open"):
                    out[direction] = "open"
                elif self.state.flag("door_unlocked"):
                    out[direction] = "unlocked"
                else:
                    out[direction] = "locked"
            elif self.state.flag(ex.gate_flag):
                out[direction] = "open"
            elif ex.hidden_while_locked:
                continue
            else:
                out[direction] = "locked"
        return out

    def _door_state(self) -> str:
        f = self.state.flags
        if f.door_open:
            return "open"
        if f.door_unlocked:
            return "unlocked"
        return "locked"

    def _lockbox_state(self) -> str:
        f = self.state.flags
        if f.lockbox_open:
            return "open"
        if f.lockbox_unlocked:
            return "unlocked"
        return "locked"

    def _safe_state(self) -> str:
        f = self.state.flags
        if f.safe_open:
            return "open"
        if f.safe_unlocked:
            return "unlocked"
        return "locked"

    def _room_description(self, room: str) -> str:
        r = ROOMS[room]
        desc = r.description
        for obj_id in r.objects:
            obj = OBJECTS.get(obj_id)
            if not obj:
                continue
            for flag, old, new in obj.room_state_replaces:
                if self.state.flag(flag):
                    desc = desc.replace(old, new)
        for flag, old, new in r.description_replaces:
            if self.state.flag(flag):
                desc = desc.replace(old, new)
        for flag, text in r.description_appends:
            if self.state.flag(flag):
                desc += text
        taken_here = self.state.items_taken_in_room(room)
        for obj_id in r.objects:
            obj = OBJECTS.get(obj_id)
            if obj and obj.room_mention and obj_id in taken_here:
                desc = desc.replace(obj.room_mention, "")
        for obj_id in r.objects:
            obj = OBJECTS.get(obj_id)
            if not obj or not obj.room_mention or obj_id in taken_here:
                continue
            prereq = obj.room_mention_reveal_after
            if prereq and prereq in taken_here:
                mention = obj.room_mention
                if desc and mention and not desc[-1].isspace():
                    desc += " "
                desc += mention
        while "  " in desc:
            desc = desc.replace("  ", " ")
        return desc

    def _object_states(self) -> Dict[str, str]:
        """UI states for visible scenery in the current room (locked / unlocked / open)."""
        room_objects = set(ROOMS[self.state.current_room].objects)
        f = self.state.flags
        candidates: Dict[str, str] = {
            "door": self._door_state(),
            "lockbox": self._lockbox_state(),
            "safe": self._safe_state(),
            "grate": "open" if f.grate_open else "closed",
        }
        if f.painting_open:
            candidates["painting"] = "open"
        return {
            key: value
            for key, value in candidates.items()
            if key in room_objects and self._object_visible_in_room(key)
        }

    # ------------------------------------------------------------------ response
    def to_response(
        self,
        text: str,
        include_room_intro: bool = False,
        image: Optional[str] = None,
        ending: Optional[str] = None,
    ) -> GameStateResponse:
        room = self.state.current_room
        intro = self._room_description(room) if include_room_intro else ""
        full_text = f"{intro}\n\n{text}".strip() if intro and text else (intro or text)
        return GameStateResponse(
            text=full_text,
            room=room,
            visible_items=self._visible_items(room),
            exits=self._exits(room),
            inventory=list(self.state.inventory),
            is_solved=self.state.flag("is_solved"),
            object_states=self._object_states(),
            image=image,
            ending=ending,
        )

    def get_state(self) -> GameStateResponse:
        """Return the current room description and visible state (no command executed)."""
        return self.to_response(self._room_description(self.state.current_room))

    def reset(self) -> GameStateResponse:
        """Discard progress and return to a fresh Chapter 0 start."""
        self.state = GameState()
        return self.get_state()

    def load_state(self, data: Dict[str, object]) -> GameStateResponse:
        """Restore a previously saved state (save/load and export/restore)."""
        self.state = GameState.from_dict(data)
        return self.get_state()

    # ------------------------------------------------------------------ dispatch
    def execute(self, command: str) -> GameStateResponse:
        """Parse and run one player command; return the resulting game state."""
        parsed = parse_command(command)
        handlers = {
            "inventory": self._handle_inventory,
            "look": self._handle_look,
            "go": self._handle_go,
            "examine": self._handle_examine,
            "read": self._handle_read,
            "take": self._handle_take,
            "use": self._handle_use,
            "open": self._handle_use,  # use/open share the rule engine
            "touch": self._handle_touch,
            "pull": self._handle_pull,
            "speak": self._handle_speak,
        }
        handler = handlers.get(parsed.verb)
        if handler is None:
            return self.to_response(UNKNOWN_VERB_MSG)
        return handler(parsed)

    def _handle_inventory(self, _parsed: ParsedCommand) -> GameStateResponse:
        if not self.state.inventory:
            return self.to_response("Your inventory is empty.")
        items = ", ".join(self._label(i) for i in self.state.inventory)
        return self.to_response(f"You are carrying: {items}.")

    def _handle_look(self, _parsed: ParsedCommand) -> GameStateResponse:
        return self.to_response(self._room_description(self.state.current_room))

    def _handle_go(self, parsed: ParsedCommand) -> GameStateResponse:
        room = self.state.current_room
        exits = ROOMS[room].exits
        direction: str | None = None

        if parsed.direction:
            direction = DIRECTION_ALIASES.get(parsed.direction, parsed.direction)
        elif parsed.target:
            obj_id = self._resolve(parsed.target)
            if obj_id:
                direction = GO_OBJECT_EXITS.get(room, {}).get(obj_id)
            if not direction:
                return self.to_response(f"You can't go there.")

        if not direction or direction not in exits:
            return self.to_response("There is no way through here.")
        ex = exits[direction]
        if ex.always_closed:
            return self.to_response(ex.locked_text)
        if ex.gate_flag and not self.state.flag(ex.gate_flag):
            return self.to_response(ex.locked_text)
        if ex.ending:
            self.state.set_flag("is_solved", True)
            return self.to_response(
                "You climb down into the shaft. The rungs groan under your "
                "weight as the reddish glow rises to swallow you whole...",
                ending=ex.ending,
            )
        self.state.current_room = ex.target
        return self.to_response("", include_room_intro=True)

    def _handle_examine(self, parsed: ParsedCommand) -> GameStateResponse:
        raw = parsed.target or ""
        obj_id = self._resolve(raw)
        if not obj_id or obj_id not in OBJECTS:
            return self.to_response(f"You don't see any {raw} here.")

        inter = self._find_interaction(
            "examine",
            frozenset({obj_id}),
            self.state.current_room,
            has_code=False,
        )
        if inter is not None:
            return self._apply_interaction(inter, has_code=False, code=None)

        if self.state.has_item(obj_id):
            obj = OBJECTS[obj_id]
            return self.to_response(
                self._examine_text(obj_id),
                image=self._examine_image(obj_id),
            )

        room = self.state.current_room
        if obj_id in ROOMS[room].objects:
            obj = OBJECTS[obj_id]
            if obj.flavor or self._object_visible_in_room(obj_id):
                return self.to_response(
                    self._examine_text(obj_id),
                    image=self._examine_image(obj_id),
                )

        return self.to_response(f"You don't see any {raw} here.")

    READ_NOTHING_MSG = "There is nothing to read."
    READ_TAKE_FIRST_MSG = "You can't read it from here, better take it first."

    def _handle_read(self, parsed: ParsedCommand) -> GameStateResponse:
        raw = parsed.target or ""
        if not raw:
            return self.to_response("What do you want to read?")

        obj_id = self._resolve(raw)
        if not obj_id or obj_id not in OBJECTS:
            return self.to_response(self.READ_NOTHING_MSG)

        obj = OBJECTS[obj_id]
        if self.state.has_item(obj_id):
            if obj.read_requires_holding:
                return self.to_response(self._describe(obj_id), image=obj.examine_image)
            return self.to_response(self.READ_NOTHING_MSG)

        room = self.state.current_room
        if obj_id in ROOMS[room].objects and (
            obj.flavor or self._object_visible_in_room(obj_id)
        ):
            if obj.read_requires_holding:
                return self.to_response(self.READ_TAKE_FIRST_MSG)
            return self.to_response(self.READ_NOTHING_MSG)

        return self.to_response(self.READ_NOTHING_MSG)

    def _handle_take(self, parsed: ParsedCommand) -> GameStateResponse:
        raw = parsed.target or ""
        obj_id = self._resolve(raw)
        if not obj_id or obj_id not in OBJECTS:
            return self.to_response(f"You don't see any {raw} here.")
        if self.state.has_item(obj_id):
            return self.to_response("You already have that.")

        obj = OBJECTS[obj_id]
        if not obj.takeable:
            return self.to_response("That can't be picked up.")

        room = self.state.current_room
        if obj_id not in ROOMS[room].objects or not self._object_visible_in_room(obj_id):
            return self.to_response(f"You don't see any {raw} here.")

        self.state.add_item(obj_id)
        self.state.mark_taken(room, obj_id)
        # `take` only moves the item into the inventory - it must never
        # spoil an `examine_image` (Phase 5-follow-up: reading/opening only happens
        # via a deliberate `examine`, once the item is actually held).
        return self.to_response(obj.take_text or f"You take the {obj.label}.")

    def _handle_touch(self, parsed: ParsedCommand) -> GameStateResponse:
        return self._handle_simple_verb(parsed, "touch", verb_default_fallback("touch"))

    def _handle_pull(self, parsed: ParsedCommand) -> GameStateResponse:
        return self._handle_simple_verb(parsed, "pull", verb_default_fallback("pull"))

    def _handle_speak(self, parsed: ParsedCommand) -> GameStateResponse:
        return self._handle_simple_verb(parsed, "speak", verb_default_fallback("speak"))

    def _handle_simple_verb(
        self, parsed: ParsedCommand, verb: str, default_text: str
    ) -> GameStateResponse:
        """Shared handler for touch/pull/speak: unlike examine/take, an
        unrecognized target never says "you don't see any X here" - it just
        falls through to `default_text`, since these verbs are meant to work
        (or harmlessly not work) on basically any word the player tries."""
        raw = parsed.target
        if not raw:
            return self.to_response(f"What do you want to {verb}?")

        obj_id = self._resolve(raw)
        if obj_id:
            inter = self._find_interaction(verb, frozenset({obj_id}), self.state.current_room, has_code=False)
            if inter is not None:
                return self._apply_interaction(inter, has_code=False, code=None)
        return self.to_response(default_text)

    # use + open both run through here
    def _handle_use(self, parsed: ParsedCommand) -> GameStateResponse:
        verb = parsed.verb
        target_raw = parsed.target or ""
        sec_raw = parsed.secondary

        obj_a = self._resolve(target_raw)
        if verb == "use" and is_safe_literal_number_attempt(target_raw, sec_raw, obj_a):
            return self.to_response(SAFE_FAKE_NUMBER_MSG)

        if target_raw and not obj_a:
            return self.to_response(f"You don't see any {target_raw} here.")

        has_code = False
        code: str | None = None
        obj_b: Optional[str] = None
        if sec_raw:
            compact = sec_raw.strip().replace(" ", "")
            if compact.isdigit():
                has_code = True
                code = compact
            else:
                obj_b = self._resolve(sec_raw)
                if not obj_b:
                    return self.to_response(f"You don't see any {sec_raw} here.")

        objs: Set[str] = set()
        if obj_a:
            objs.add(obj_a)
        if obj_b:
            objs.add(obj_b)

        # Red herring (only on `use`)
        if verb == "use":
            for oid in objs:
                if oid in RED_HERRINGS:
                    return self.to_response(RED_HERRINGS[oid])

        inter = self._find_interaction(verb, frozenset(objs), self.state.current_room, has_code)
        if inter is None:
            return self.to_response("That doesn't work here.")
        return self._apply_interaction(inter, has_code, code)

    def _interaction_applicable(self, inter: Interaction, has_code: bool) -> bool:
        """Skip rules whose ``needs_flags_false`` or code-lock shape don't fit.

        ``needs_flags_true`` failures are handled in ``_apply_interaction`` so
        a single verb/object pair can still return ``blocked_text`` (e.g.
        ``open lockbox`` while locked).
        """
        if has_code and inter.code_for is None:
            return False
        if not has_code and inter.code_for is not None:
            return False
        for flag in inter.needs_flags_false:
            if self.state.flag(flag):
                return False
        return True

    def _find_interaction(
        self, verb: str, objs: frozenset[str], room: str, has_code: bool
    ) -> Optional[Interaction]:
        for i in INTERACTIONS:
            if i.room != room or verb not in i.verbs or i.objects != objs:
                continue
            if not self._interaction_applicable(i, has_code):
                continue
            return i
        return None

    def _apply_interaction(
        self, inter: Interaction, has_code: bool, code: str | None
    ) -> GameStateResponse:
        if inter.already_flag and self.state.flag(inter.already_flag):
            return self.to_response(inter.already_text)

        for flag in inter.needs_flags_true:
            if not self.state.flag(flag):
                return self.to_response(inter.blocked_text)
        for flag in inter.needs_flags_false:
            if self.state.flag(flag):
                return self.to_response(inter.blocked_text)

        for item in inter.needs_inventory:
            if not self.state.has_item(item):
                return self.to_response(f"You don't have the {self._label(item)}.")

        if inter.code_for is not None:
            if code == CODE:
                self._apply_effect(inter.effect)
                return self.to_response(inter.success_text)
            return self.to_response(inter.wrong_code_text)

        self._apply_effect(inter.effect)
        return self.to_response(
            inter.success_text,
            include_room_intro=bool(inter.effect.move_to_room),
        )

    def _apply_effect(self, effect: Effect) -> None:
        for name, value in effect.set_flags:
            self.state.set_flag(name, value)
        for item in effect.add_items:
            self.state.add_item(item)
        for item in effect.remove_items:
            self.state.remove_item(item)
        if effect.move_to_room:
            self.state.current_room = effect.move_to_room
        if effect.solved:
            self.state.set_flag("is_solved", True)


def create_session() -> GameSession:
    """Start a new session and register it in the in-memory store."""
    session = GameSession()
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> GameSession | None:
    """Look up an active session by id, or ``None`` if unknown."""
    return _sessions.get(session_id)


def reset_session(session_id: str) -> GameSession | None:
    """Reset an existing session in place; used by tests and ``POST /reset``."""
    session = _sessions.get(session_id)
    if session:
        session.reset()
    return session
