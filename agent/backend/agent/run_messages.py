"""LangChain message parsing and step-history reconstruction."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from db.models import StepRecord

_BLOCKED_RE = re.compile(r"^Command blocked: '(.*?)' — (.*)$")


def message_text(message: Any) -> str:
    """Extract human-readable text from LangChain message chunks or outputs."""
    if message is None:
        return ""
    content = getattr(message, "content", "")
    parts: list[str] = []
    if isinstance(content, str):
        if content.strip():
            parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                if block.strip():
                    parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type in ("text", "output_text"):
                    parts.append(str(block.get("text", "")))
                elif block_type in ("thinking", "reasoning"):
                    parts.append(
                        str(
                            block.get("thinking")
                            or block.get("reasoning")
                            or block.get("text", "")
                        )
                    )
                elif "text" in block:
                    parts.append(str(block["text"]))
    elif content:
        parts.append(str(content))

    kwargs = getattr(message, "additional_kwargs", None) or {}
    for key in ("reasoning_content", "reasoning", "thinking"):
        extra = kwargs.get(key)
        if extra:
            parts.append(str(extra))

    return "\n".join(part for part in (segment.strip() for segment in parts) if part)


def has_tool_calls(message: Any) -> bool:
    if message is None:
        return False
    tool_calls = getattr(message, "tool_calls", None) or []
    return bool(tool_calls)


def thought_from_message(message: Any, stream_buffer: list[str] | None = None) -> str:
    """Extract displayable thought text from a completed LLM message or stream buffer."""
    thought = message_text(message)
    if not thought and stream_buffer:
        thought = "".join(stream_buffer)
    return thought.strip()


def rebuild_messages_from_steps(steps: list[StepRecord], goal: str) -> list:
    """Reconstruct LangChain message history from stored steps for continue-run."""
    messages: list = [HumanMessage(content=goal)]
    pending_thoughts: list[str] = []

    def flush_action(command: str, observation: str) -> None:
        call_id = f"continue_{uuid4().hex[:8]}"
        thought_text = "\n".join(pending_thoughts).strip()
        pending_thoughts.clear()
        messages.append(
            AIMessage(
                content=thought_text,
                tool_calls=[
                    {"name": "send_command", "args": {"command": command}, "id": call_id}
                ],
            )
        )
        messages.append(ToolMessage(content=observation, tool_call_id=call_id))

    i = 0
    n = len(steps)
    while i < n:
        step = steps[i]
        if step.type == "thought":
            pending_thoughts.append(step.content)
            i += 1
            continue
        if step.type == "action" and step.content.startswith("send_command:"):
            command = step.content[len("send_command:") :].strip()
            j = i + 1
            while j < n and steps[j].type not in ("observation", "action"):
                j += 1
            if j < n and steps[j].type == "observation":
                observation = steps[j].content
                i = j + 1
            else:
                observation = json.dumps({"text": "(observation lost — continue from here)"})
                i += 1
            flush_action(command, observation)
            continue
        if step.type == "blocked":
            match = _BLOCKED_RE.match(step.content)
            command = match.group(1) if match else "unknown"
            reason = match.group(2) if match else step.content
            flush_action(command, json.dumps({"error": reason, "text": reason}))
            i += 1
            continue
        i += 1

    return messages
