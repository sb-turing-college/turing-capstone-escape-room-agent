"""Optional Mistral moderation for agent commands."""

from __future__ import annotations

import re

import httpx

from agent.game_secrets import SAFE_CODE_ALLOWLIST
from config import get_settings

MISTRAL_MODERATION_URL = "https://api.mistral.ai/v1/moderations"

# Mistral's moderation model (mistral-moderation-2603) flags common adventure-game
# verbs (e.g. "open lockbox", "use key with door") under "criminal"/"dangerous" with
# high confidence, since it has no context that this is a fixed, non-interactive
# text adventure. We therefore only act on categories that indicate genuine misuse
# of the LLM/tool itself, and ignore categories that are near-guaranteed false
# positives for in-game verbs like "steal", "unlock", "break".
#
# Full category list returned by the API: sexual, hate_and_discrimination,
# violence_and_threats, dangerous, criminal, selfharm, health, financial, law,
# pii, jailbreaking.
ENFORCED_CATEGORIES = {
    "hate_and_discrimination",
    "sexual",
    "selfharm",
    "pii",
    "jailbreaking",
}

# The safe combination in this specific game reads like a phone number / ID to the
# moderation model and gets flagged as "pii". Since this agent only ever plays this
# one fixed adventure, we allowlist the known code (see agent/game_secrets.py) so
# the safe puzzle isn't silently blocked, while "pii" stays enforced for everything
# else (e.g. if a model ever echoes a real address or phone number).
_NUMBER_TOKEN_RE = re.compile(r"\d+")


def _pii_allowlisted(command: str) -> bool:
    tokens = set(_NUMBER_TOKEN_RE.findall(command))
    return bool(tokens & SAFE_CODE_ALLOWLIST)


async def moderate_command(command: str) -> tuple[bool, str | None]:
    """Return (allowed, reason). If no API key, always allow."""
    settings = get_settings()
    api_key = str(settings["mistral_api_key"])
    if not api_key:
        return True, None

    payload = {
        "model": "mistral-moderation-latest",
        "input": command,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(MISTRAL_MODERATION_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    if not results:
        return True, None

    categories = results[0].get("categories", {})
    blocked = [
        name
        for name, flagged in categories.items()
        if flagged and name in ENFORCED_CATEGORIES
    ]
    if "pii" in blocked and _pii_allowlisted(command):
        blocked = [name for name in blocked if name != "pii"]
    if blocked:
        return False, f"Blocked categories: {', '.join(blocked)}"
    return True, None
