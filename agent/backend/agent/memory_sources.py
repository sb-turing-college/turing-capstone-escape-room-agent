"""ChromaDB memory entry ``source`` metadata — canonical keys and legacy aliases."""

from __future__ import annotations

AGENT_CHAT = "agent_chat"
IN_GAME_REFLECTION = "in_game_reflection"
FALLBACK_SUMMARY = "fallback_summary"

LEGACY_AGENT_CHAT = "interview"
LEGACY_IN_GAME_REFLECTION = "agent_reflection"
LEGACY_FALLBACK_SUMMARY = "run_summary"

ALL_MEMORY_SOURCES = frozenset(
    {
        AGENT_CHAT,
        IN_GAME_REFLECTION,
        FALLBACK_SUMMARY,
        LEGACY_AGENT_CHAT,
        LEGACY_IN_GAME_REFLECTION,
        LEGACY_FALLBACK_SUMMARY,
    }
)


def normalize_memory_source(source: str | None) -> str:
    """Map legacy Chroma metadata to canonical source keys."""
    if source in (LEGACY_AGENT_CHAT, AGENT_CHAT):
        return AGENT_CHAT
    if source in (LEGACY_IN_GAME_REFLECTION, IN_GAME_REFLECTION):
        return IN_GAME_REFLECTION
    if source in (LEGACY_FALLBACK_SUMMARY, FALLBACK_SUMMARY):
        return FALLBACK_SUMMARY
    return FALLBACK_SUMMARY


def is_agent_chat_source(source: str | None) -> bool:
    return source in (AGENT_CHAT, LEGACY_AGENT_CHAT)
