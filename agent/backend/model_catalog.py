"""Model catalog: OpenRouter (env) + ACM direct Google/Anthropic IDs.

Keep ACM_* lists in sync with:
  ai-context-manager/ui/src/config/models.ts (ALL_MODELS ids).
"""

from __future__ import annotations

from typing import Any, Literal

Provider = Literal["openrouter", "google", "anthropic"]

OPENROUTER_GROUP_LABEL = "OpenRouter"
GOOGLE_GROUP_LABEL = "Google Gemini"
ANTHROPIC_GROUP_LABEL = "Anthropic Claude"

# ACM direct model ids (no provider path prefix). Display = id (unchanged for logging).
ACM_GOOGLE_MODELS: list[str] = [
    "gemini-3-flash-preview",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-pro-preview",
    "gemini-3.1-pro-preview",
]

ACM_ANTHROPIC_MODELS: list[str] = [
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-opus-4-5",
    "claude-opus-4-6",
    "claude-opus-5",
]

_PROVIDER_ENV: dict[Provider, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def resolve_provider(model: str) -> Provider:
    """Route by id shape: path → OpenRouter; gemini-/claude- → direct APIs."""
    if "/" in model:
        return "openrouter"
    if model.startswith("gemini-"):
        return "google"
    if model.startswith("claude-"):
        return "anthropic"
    raise ValueError(
        f"Unknown model id {model!r}: expected OpenRouter slug (with '/'), "
        "or gemini-* / claude-* direct id."
    )


def provider_env_name(provider: Provider) -> str:
    return _PROVIDER_ENV[provider]


def provider_key_configured(provider: Provider, settings: dict[str, Any]) -> bool:
    key_map = {
        "openrouter": "openrouter_api_key",
        "google": "google_api_key",
        "anthropic": "anthropic_api_key",
    }
    return bool(str(settings.get(key_map[provider], "") or "").strip())


def model_key_configured(model: str, settings: dict[str, Any]) -> bool:
    return provider_key_configured(resolve_provider(model), settings)


def missing_key_detail(model: str) -> str:
    env_name = provider_env_name(resolve_provider(model))
    return f"{env_name} not configured (required for model {model})."


def build_model_groups(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Grouped catalog for the UI; each model carries a disabled flag."""
    openrouter_models = list(settings["available_models"])
    groups: list[dict[str, Any]] = [
        {
            "label": OPENROUTER_GROUP_LABEL,
            "models": [
                {
                    "id": mid,
                    "disabled": not provider_key_configured("openrouter", settings),
                }
                for mid in openrouter_models
            ],
        },
        {
            "label": GOOGLE_GROUP_LABEL,
            "models": [
                {
                    "id": mid,
                    "disabled": not provider_key_configured("google", settings),
                }
                for mid in ACM_GOOGLE_MODELS
            ],
        },
        {
            "label": ANTHROPIC_GROUP_LABEL,
            "models": [
                {
                    "id": mid,
                    "disabled": not provider_key_configured("anthropic", settings),
                }
                for mid in ACM_ANTHROPIC_MODELS
            ],
        },
    ]
    return groups


def flat_model_ids(groups: list[dict[str, Any]]) -> list[str]:
    return [m["id"] for g in groups for m in g["models"]]


def first_enabled_model(groups: list[dict[str, Any]]) -> str | None:
    for group in groups:
        for model in group["models"]:
            if not model["disabled"]:
                return str(model["id"])
    return None


def resolve_default_explorer(settings: dict[str, Any], groups: list[dict[str, Any]]) -> str:
    configured = str(settings["default_explorer_model"])
    if model_key_configured(configured, settings):
        return configured
    return first_enabled_model(groups) or configured


def resolve_memory_model(
    explorer_model: str,
    memory_model: str | None,
    settings: dict[str, Any],
) -> str:
    """Use configured memory model when its key exists; else fall back to explorer.

    Memory summarization is invisible in the UI; without this fallback a
    Gemini-only .env (no OpenRouter) would fail even when the explorer model
    is enabled.
    """
    candidate = (memory_model or str(settings["default_memory_model"])).strip()
    if candidate and model_key_configured(candidate, settings):
        return candidate
    return explorer_model
