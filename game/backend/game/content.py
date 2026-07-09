"""Game content as pure data — re-exports split modules."""

from __future__ import annotations

from .interactions import Effect, INTERACTIONS, Interaction, RED_HERRINGS
from .objects import ALIAS_TO_ID, AMBIGUOUS_NOTE, OBJECTS, GameObject
from .rooms import GO_OBJECT_EXITS, ROOMS, Exit, Room
from .verbs import (
    CODE,
    DIRECTION_ALIASES,
    FAVORITE_A,
    FAVORITE_B,
    LOCKED_MSG,
    SAFE_CODE_HINT,
    SAFE_FAKE_NUMBER_MSG,
    VERBS,
    is_safe_literal_number_attempt,
)
