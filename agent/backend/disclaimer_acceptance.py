"""Local disclaimer acceptance (clickwrap) before LLM-costing agent actions."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from config import get_settings

# agent/backend/disclaimer_acceptance.py -> agent/
AGENT_ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER_MARKER = AGENT_ROOT / ".disclaimer_accepted"
DISCLAIMER_FILE = AGENT_ROOT.parent / "DISCLAIMER.md"

DISCLAIMER_DOC = "DISCLAIMER.md (repository root)"
DISCLAIMER_REJECT_DETAIL = (
    f"Disclaimer not accepted. Read {DISCLAIMER_DOC}, then accept via the "
    "Escape Room Agent dashboard or POST /agent/disclaimer/accept."
)


def _env_disclaimer_accepted() -> bool:
    settings = get_settings()
    return bool(settings.get("disclaimer_accepted"))


def is_disclaimer_accepted() -> bool:
    if _env_disclaimer_accepted():
        return True
    return DISCLAIMER_MARKER.is_file()


def accept_disclaimer() -> None:
    DISCLAIMER_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DISCLAIMER_MARKER.touch(exist_ok=True)


def require_disclaimer_accepted() -> None:
    if is_disclaimer_accepted():
        return
    raise HTTPException(status_code=403, detail=DISCLAIMER_REJECT_DETAIL)


def ensure_disclaimer_accepted_interactive() -> None:
    if is_disclaimer_accepted():
        return
    print(
        "\nWARNING: This autonomous AI agent may incur third-party LLM API costs.\n"
        f"Read {DISCLAIMER_DOC} before continuing.\n"
        "Type ACCEPT to proceed: ",
        end="",
        flush=True,
    )
    if input().strip() != "ACCEPT":
        raise SystemExit("Aborted: disclaimer not accepted.")
    accept_disclaimer()
    print("Disclaimer accepted.\n")
