"""SQLAlchemy setup for agent run history."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(str(settings["database_url"]), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    """Add columns introduced after first deploy (SQLite has no auto-migrate)."""
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(runs)").fetchall()
        columns = {row[1] for row in rows}
        if "game_state_json" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN game_state_json JSON"
            )
            conn.commit()
        if "continued_from_run_id" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN continued_from_run_id VARCHAR"
            )
            conn.commit()
        if "memory_session_id" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN memory_session_id VARCHAR"
            )
            conn.commit()
        if "max_human_assists" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN max_human_assists INTEGER DEFAULT 0"
            )
            conn.commit()
        if "human_assists_used" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN human_assists_used INTEGER DEFAULT 0"
            )
            conn.commit()
        if "is_fresh_attempt" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN is_fresh_attempt BOOLEAN DEFAULT 0"
            )
            conn.commit()
        if "max_steps" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN max_steps INTEGER"
            )
            conn.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
