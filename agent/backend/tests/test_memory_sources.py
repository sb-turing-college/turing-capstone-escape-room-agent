"""Tests for memory source canonical keys and legacy dual-read."""

from __future__ import annotations

from agent.memory_sources import (
    AGENT_CHAT,
    FALLBACK_SUMMARY,
    IN_GAME_REFLECTION,
    is_agent_chat_source,
    normalize_memory_source,
)


def test_normalize_memory_source_maps_legacy_keys():
    assert normalize_memory_source("interview") == AGENT_CHAT
    assert normalize_memory_source("agent_reflection") == IN_GAME_REFLECTION
    assert normalize_memory_source("run_summary") == FALLBACK_SUMMARY


def test_normalize_memory_source_preserves_canonical_keys():
    assert normalize_memory_source(AGENT_CHAT) == AGENT_CHAT
    assert normalize_memory_source(IN_GAME_REFLECTION) == IN_GAME_REFLECTION
    assert normalize_memory_source(FALLBACK_SUMMARY) == FALLBACK_SUMMARY


def test_normalize_memory_source_unknown_defaults_to_fallback():
    assert normalize_memory_source(None) == FALLBACK_SUMMARY
    assert normalize_memory_source("unknown") == FALLBACK_SUMMARY


def test_is_agent_chat_source_accepts_legacy_and_canonical():
    assert is_agent_chat_source("interview") is True
    assert is_agent_chat_source(AGENT_CHAT) is True
    assert is_agent_chat_source(IN_GAME_REFLECTION) is False
