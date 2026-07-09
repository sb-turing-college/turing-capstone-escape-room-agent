"""Shared pytest fixtures for capstone-agent backend tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

# Keep API / SessionLocal tests off the developer's live agent.db.
_TEST_ROOT = Path(tempfile.gettempdir()) / "capstone_agent_pytest"
_TEST_ROOT.mkdir(exist_ok=True)
_TEST_DB = _TEST_ROOT / "agent_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ.setdefault("CHROMA_PERSIST_DIR", str(_TEST_ROOT / "chroma_test"))
os.environ.setdefault("OPENROUTER_API_KEY", "pytest-dummy-key-not-used-in-unit-tests")
os.environ.setdefault("DISCLAIMER_ACCEPTED", "1")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import get_settings

get_settings.cache_clear()

from agent.game_client import GameClient
from db.database import Base, get_db, init_db

GAME_API_BASE_URL = os.getenv("GAME_API_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Generator[None, None, None]:
    """Avoid stale lru_cache after tests patch OPENROUTER_API_KEY."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _isolated_app_database() -> Generator[None, None, None]:
    """Fresh SQLite file for TestClient routes; never touches ./agent.db."""
    get_settings.cache_clear()
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    init_db()
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def api_db_session() -> Generator[Session, None, None]:
    """In-memory DB safe for FastAPI TestClient (background threads)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def api_client(api_db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient backed by an isolated in-memory database."""
    from main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield api_db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def game_client() -> GameClient:
    client = GameClient(GAME_API_BASE_URL)
    yield client
    await client.close()
