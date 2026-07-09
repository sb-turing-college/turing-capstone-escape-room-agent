"""SQLAlchemy setup for SQLite."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./capstone.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_LEGACY_TABLES = ("steps", "sessions", "runs")


class Base(DeclarativeBase):
    pass


def _migrate_sqlite_schema() -> None:
    """Drop unused legacy tables from early monorepo planning (agent data lives in capstone-agent)."""
    if not str(DATABASE_URL).startswith("sqlite"):
        return

    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        existing = {row[0] for row in rows}
        if not existing.intersection(_LEGACY_TABLES):
            return

        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table in _LEGACY_TABLES:
            if table in existing:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.commit()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
