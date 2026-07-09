"""ORM models for saved games."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .datetime_utils import utc_now


class SavedGameRecord(Base):
    """One save slot (Phase 2c). Three slots per `client_id` (browser/device,
    no login), identified by a UUID stored in `localStorage`."""

    __tablename__ = "saved_games"
    __table_args__ = (UniqueConstraint("client_id", "slot", name="uq_saved_games_client_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String, index=True)
    slot: Mapped[int] = mapped_column(Integer)
    state_json: Mapped[str] = mapped_column(Text)
    room: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
