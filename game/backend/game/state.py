"""Game state — separate from game content (content modules)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Set


@dataclass
class GameFlags:
    """Boolean puzzle and progression flags. Add a field here for new puzzles."""

    door_unlocked: bool = False
    door_open: bool = False
    lockbox_unlocked: bool = False
    lockbox_open: bool = False
    painting_open: bool = False
    safe_unlocked: bool = False
    safe_open: bool = False
    # `is_solved` reflects the actual demo ending (Exit.ending), not any
    # individual puzzle step - see engine.py's exit handling.
    is_solved: bool = False
    chimney_ladder_visible: bool = False
    grate_open: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameFlags":
        # Unknown keys (e.g. from an older save with removed flags) are dropped;
        # missing keys fall back to dataclass defaults.
        known = {f.name for f in fields(cls)}
        return cls(**{key: bool(value) for key, value in data.items() if key in known})


@dataclass
class GameState:
    """Mutable engine state: room, inventory, taken-item tracking, and flags."""

    current_room: str = "library"
    inventory: List[str] = field(default_factory=list)
    taken_from_rooms: Dict[str, Set[str]] = field(default_factory=dict)
    flags: GameFlags = field(default_factory=GameFlags)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable form for save/load (Phase 2c)."""
        return {
            "current_room": self.current_room,
            "inventory": list(self.inventory),
            "taken_from_rooms": {
                room: sorted(items) for room, items in self.taken_from_rooms.items()
            },
            "flags": self.flags.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        current_room = data.get("current_room", "library")
        if current_room == "secret_chamber":
            current_room = "lords_office"
        taken_from_rooms: Dict[str, Set[str]] = {}
        for room, items in data.get("taken_from_rooms", {}).items():
            room_key = "lords_office" if room == "secret_chamber" else room
            taken_from_rooms[room_key] = set(items)
        return cls(
            current_room=current_room,
            inventory=list(data.get("inventory", [])),
            taken_from_rooms=taken_from_rooms,
            flags=GameFlags.from_dict(data.get("flags", {})),
        )

    def items_taken_in_room(self, room: str) -> Set[str]:
        return self.taken_from_rooms.setdefault(room, set())

    def mark_taken(self, room: str, item_id: str) -> None:
        self.items_taken_in_room(room).add(item_id)

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory

    def add_item(self, item_id: str) -> None:
        if item_id not in self.inventory:
            self.inventory.append(item_id)

    def remove_item(self, item_id: str) -> None:
        if item_id in self.inventory:
            self.inventory.remove(item_id)

    def flag(self, name: str) -> bool:
        return bool(getattr(self.flags, name))

    def set_flag(self, name: str, value: bool) -> None:
        setattr(self.flags, name, value)
