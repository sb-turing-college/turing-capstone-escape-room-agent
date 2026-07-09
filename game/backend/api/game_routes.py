"""REST endpoints for the text adventure."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from db.database import get_db
from db.datetime_utils import utc_now
from db.models import SavedGameRecord
from game.engine import create_session, get_session, reset_session
from game.game_constants import available_verbs

router = APIRouter(prefix="/game", tags=["game"])

SAVE_SLOTS = (1, 2, 3)


def _validate_slot(slot: int) -> None:
    if slot not in SAVE_SLOTS:
        raise HTTPException(status_code=400, detail="Slot must be 1, 2, or 3.")


class ActionRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=500)


class GameResponse(BaseModel):
    session_id: str | None = None
    text: str
    room: str
    visible_items: list[str]
    exits: dict[str, str]
    inventory: list[str]
    is_solved: bool
    object_states: dict[str, str] = Field(default_factory=dict)
    available_verbs: list[str] = Field(default_factory=available_verbs)
    image: str | None = None
    ending: str | None = None


class ClientRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=200)


class SaveActionResponse(BaseModel):
    slot: int
    room: str
    updated_at: str


class SaveSlotInfo(BaseModel):
    slot: int
    empty: bool
    room: str | None = None
    updated_at: str | None = None


def _to_response(session_id: str, state) -> GameResponse:
    return GameResponse(
        session_id=session_id,
        text=state.text,
        room=state.room,
        visible_items=state.visible_items,
        exits=state.exits,
        inventory=state.inventory,
        is_solved=state.is_solved,
        object_states=state.object_states,
        available_verbs=state.available_verbs,
        image=state.image,
        ending=state.ending,
    )


class RestoreRequest(BaseModel):
    state: dict = Field(..., description="Raw GameState.to_dict() payload")


@router.get("/{session_id}/export-state")
def export_state(session_id: str) -> dict:
    """Return raw ``GameState.to_dict()`` for agent snapshot / restore."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session.state.to_dict()


@router.post("/restore", response_model=GameResponse)
def restore_game(body: RestoreRequest) -> GameResponse:
    """Create a new session from an exported state dict (agent spectate recovery)."""
    session = create_session()
    state = session.load_state(body.state)
    return _to_response(session.session_id, state)


@router.post("/new", response_model=GameResponse)
def new_game() -> GameResponse:
    """Start a fresh Chapter 0 session."""
    session = create_session()
    state = session.get_state()
    return _to_response(session.session_id, state)


@router.post("/{session_id}/action", response_model=GameResponse)
def game_action(session_id: str, body: ActionRequest) -> GameResponse:
    """Execute one text command in an existing session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    state = session.execute(body.command)
    return _to_response(session_id, state)


@router.get("/{session_id}/state", response_model=GameResponse)
def game_state(session_id: str) -> GameResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    state = session.get_state()
    return _to_response(session_id, state)


@router.post("/{session_id}/reset", response_model=GameResponse)
def game_reset(session_id: str) -> GameResponse:
    session = reset_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    state = session.get_state()
    return _to_response(session_id, state)


@router.get("/saves", response_model=list[SaveSlotInfo])
def list_saves(client_id: str, db: DbSession = Depends(get_db)) -> list[SaveSlotInfo]:
    """List all three save slots for a browser ``client_id``."""
    records = {
        record.slot: record
        for record in db.query(SavedGameRecord).filter_by(client_id=client_id).all()
    }
    return [
        SaveSlotInfo(slot=slot, empty=False, room=records[slot].room, updated_at=records[slot].updated_at.isoformat())
        if slot in records
        else SaveSlotInfo(slot=slot, empty=True)
        for slot in SAVE_SLOTS
    ]


@router.post("/{session_id}/save/{slot}", response_model=SaveActionResponse)
def save_game(
    session_id: str, slot: int, body: ClientRequest, db: DbSession = Depends(get_db)
) -> SaveActionResponse:
    """Persist the current session to slot 1–3 for ``client_id``."""
    _validate_slot(slot)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    record = (
        db.query(SavedGameRecord)
        .filter_by(client_id=body.client_id, slot=slot)
        .one_or_none()
    )
    if record is None:
        record = SavedGameRecord(client_id=body.client_id, slot=slot)
        db.add(record)

    record.state_json = json.dumps(session.state.to_dict())
    record.room = session.state.current_room
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)

    return SaveActionResponse(slot=slot, room=record.room, updated_at=record.updated_at.isoformat())


@router.post("/{session_id}/load/{slot}", response_model=GameResponse)
def load_game(
    session_id: str, slot: int, body: ClientRequest, db: DbSession = Depends(get_db)
) -> GameResponse:
    """Restore a saved slot into the given live session."""
    _validate_slot(slot)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    record = (
        db.query(SavedGameRecord)
        .filter_by(client_id=body.client_id, slot=slot)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="This save slot is empty.")

    state = session.load_state(json.loads(record.state_json))
    return _to_response(session_id, state)
