"""Environment-backed settings."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings() -> dict[str, str | int | list[str]]:
    models_raw = os.getenv(
        "AVAILABLE_MODELS",
        "google/gemini-2.5-flash,openai/gpt-4o-mini,openai/gpt-5.5,"
        "z-ai/glm-5.2,anthropic/claude-opus-4.7",
    )
    return {
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "game_api_base_url": os.getenv("GAME_API_BASE_URL", "http://127.0.0.1:8000"),
        "database_url": os.getenv("DATABASE_URL", "sqlite:///./agent.db"),
        "chroma_persist_dir": os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
        "cors_origins": [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5174").split(",")
        ],
        "default_explorer_model": os.getenv(
            "DEFAULT_EXPLORER_MODEL", "google/gemini-2.5-flash"
        ),
        "default_memory_model": os.getenv(
            "DEFAULT_MEMORY_MODEL", "google/gemini-2.5-flash"
        ),
        "available_models": [m.strip() for m in models_raw.split(",") if m.strip()],
        "mistral_api_key": os.getenv("MISTRAL_API_KEY", ""),
        "default_max_steps": int(os.getenv("DEFAULT_MAX_STEPS", "50")),
        # Idle timeout: max seconds without ANY agent activity (LLM token, tool
        # call, tool result) before a run round is considered hung. This is NOT
        # a total-duration timeout for the whole round — a round can legitimately
        # run much longer than this if the model keeps making steady progress
        # (see agent/runner.py::_invoke_agent_with_thoughts for why).
        "llm_round_timeout_sec": int(os.getenv("LLM_ROUND_TIMEOUT_SEC", "120")),
        "agent_stuck_idle_sec": int(os.getenv("AGENT_STUCK_IDLE_SEC", "30")),
        "disclaimer_accepted": os.getenv("DISCLAIMER_ACCEPTED", "").strip().lower()
        in ("1", "true", "yes"),
    }
