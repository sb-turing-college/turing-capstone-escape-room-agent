"""Tests for ChromaStore persistence."""

from __future__ import annotations

import gc
from pathlib import Path

import pytest

from memory.chroma_store import ChromaStore

_TEST_META = {"source": "test"}


@pytest.fixture
def chroma_dir(tmp_path: Path) -> str:
    return str(tmp_path / "chroma")


def test_add_query_and_list(chroma_dir: str):
    store = ChromaStore(chroma_dir)
    assert store.count == 0

    store.add(
        "mem-1",
        "Found the memo in the parlor.",
        {"source": "run_summary", "run_id": "r1"},
    )
    assert store.count == 1

    hits = store.query("memo parlor", n_results=1)
    assert len(hits) == 1
    assert "memo" in hits[0]["document"].lower()

    entries = store.list_entries()
    assert len(entries) == 1
    assert entries[0]["id"] == "mem-1"

    del store
    gc.collect()


def test_list_entries_sorts_chronologically(chroma_dir: str):
    store = ChromaStore(chroma_dir)
    store.add(
        "mem-new",
        "Newer note.",
        {"source": "run_summary", "created_at": "2026-01-02T12:00:00+00:00"},
    )
    store.add(
        "mem-old",
        "Older note.",
        {"source": "run_summary", "created_at": "2026-01-01T10:00:00+00:00"},
    )

    entries = store.list_entries()
    assert [entry["id"] for entry in entries] == ["mem-old", "mem-new"]

    del store
    gc.collect()


def test_clear_removes_all_entries(chroma_dir: str):
    store = ChromaStore(chroma_dir)
    store.add("a", "one", _TEST_META)
    store.add("b", "two", _TEST_META)
    removed = store.clear()
    assert removed == 2
    assert store.count == 0
    assert store.clear() == 0

    del store
    gc.collect()
