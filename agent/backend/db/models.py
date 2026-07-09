"""ORM models for agent runs and steps."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base
from db.datetime_utils import utc_now


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success: Mapped[bool | None] = mapped_column(nullable=True)
    steps_count: Mapped[int] = mapped_column(Integer, default=0)
    explorer_model: Mapped[str] = mapped_column(String)
    memory_model: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Last raw GameState.to_dict() snapshot for spectate restore after game-backend restart.
    game_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Set when this run was started via "Continue Run" from an earlier run
    # that ended at its step limit (or was stopped) without succeeding.
    continued_from_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # True when started via "New Attempt" (fresh game, same memory session).
    is_fresh_attempt: Mapped[bool] = mapped_column(default=False)
    # Episodic memory scope: root run id of this playthrough chain (Option B).
    memory_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    max_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_human_assists: Mapped[int] = mapped_column(Integer, default=0)
    human_assists_used: Mapped[int] = mapped_column(Integer, default=0)

    steps: Mapped[list["StepRecord"]] = relationship(
        "StepRecord", back_populates="run", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessageRecord"]] = relationship(
        "ChatMessageRecord", back_populates="run", cascade="all, delete-orphan"
    )


class StepRecord(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"))
    step_number: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    room: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    # Extra structured payload (e.g. room_visited's from/label, item_discovered's
    # item, game_update's visible_items/inventory/exits) so a client can fully
    # rehydrate map/game-state after a page refresh, not just the WS live stream.
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    run: Mapped["RunRecord"] = relationship("RunRecord", back_populates="steps")


class ChatMessageRecord(Base):
    """Post-run interview chat messages tied to a single run.

    Separate from ChromaDB memory — new runs never read this table.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"))
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    run: Mapped["RunRecord"] = relationship("RunRecord", back_populates="chat_messages")
