"""Infer persisted max_steps for legacy runs from stored step content."""

from __future__ import annotations

import json
import re
from typing import Any

_NUDGE_MAX_RE = re.compile(
    r"commands_used=\d+/(\d+)|Run status:\s*commands_used=\d+/(\d+)"
)
_REMAINING_MAX_RE = re.compile(r"(\d+)/(\d+)\s+remaining")


def _budget_from_json(content: str) -> int | None:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    used = payload.get("commands_used")
    remaining = payload.get("commands_remaining")
    if isinstance(used, int) and isinstance(remaining, int) and used >= 0 and remaining >= 0:
        return used + remaining
    return None


def infer_max_steps_from_step_contents(contents: list[str]) -> int | None:
    """Best-effort segment budget for runs created before runs.max_steps existed."""
    for content in reversed(contents):
        inferred = _budget_from_json(content)
        if inferred is not None:
            return inferred

    for content in reversed(contents):
        for pattern in (_NUDGE_MAX_RE, _REMAINING_MAX_RE):
            match = pattern.search(content)
            if not match:
                continue
            groups = [group for group in match.groups() if group is not None]
            if groups:
                return int(groups[-1])

    return None


def infer_max_steps_from_steps(steps: list[dict[str, Any]]) -> int | None:
    """Steps as dicts with at least ``type`` and ``content`` keys."""
    observation_contents = [
        str(step.get("content") or "")
        for step in steps
        if step.get("type") == "observation" and step.get("content")
    ]
    if observation_contents:
        inferred = infer_max_steps_from_step_contents(observation_contents)
        if inferred is not None:
            return inferred

    other_contents = [
        str(step.get("content") or "")
        for step in steps
        if step.get("content")
    ]
    return infer_max_steps_from_step_contents(other_contents)
