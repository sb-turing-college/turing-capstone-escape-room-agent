"""Tests for model-specific explorer system prompts and reasoning effort."""

from __future__ import annotations

from agent.prompts import (
    build_explorer_prompt,
    explorer_prompt_suffix,
    explorer_reasoning_effort,
)


def test_default_model_has_no_suffix():
    assert explorer_prompt_suffix("google/gemini-2.5-flash") == ""


def test_default_model_uses_low_reasoning_effort():
    assert explorer_reasoning_effort("google/gemini-2.5-flash") == "low"


def test_claude_opus_47_uses_default_low_reasoning_effort():
    # "medium" showed no observed improvement over "low" for the empty-thought
    # issue (output_config.effort doesn't force explanatory text), so Opus 4.7
    # uses the same default as every other model.
    assert explorer_reasoning_effort("anthropic/claude-opus-4.7") == "low"


def test_claude_opus_47_gets_thought_suffix():
    suffix = explorer_prompt_suffix("anthropic/claude-opus-4.7")
    assert "1–2 sentences" in suffix
    assert "room name" in suffix


def test_build_explorer_prompt_appends_suffix_for_opus():
    prompt = build_explorer_prompt("anthropic/claude-opus-4.7", "prior clue")
    assert "Prior run memory (structured):\nprior clue" in prompt
    assert "Memory priority (critical)" in prompt
    assert "Model-specific (Claude Opus 4.7)" in prompt
    assert prompt.endswith(
        "- Never reply with only a room name or a command as your thought.\n"
    )


def test_build_explorer_prompt_unchanged_for_other_models():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "")
    assert "Model-specific" not in prompt
    assert "Prior run memory (structured):\nNo prior runs yet." in prompt


def test_build_explorer_prompt_includes_synced_verbs():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "")
    assert "touch" in prompt
    assert "use X with Y" in prompt
    assert "pull" in prompt


def test_build_explorer_prompt_includes_human_assist_when_enabled():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "", max_human_assists=2)
    assert "ask_human" in prompt
    assert "2 time(s)" in prompt
    assert "send_command, get_state, OR ask_human" in prompt
    assert "do NOT wait until commands_remaining is 0" in prompt
    assert "plan strategically" in prompt


def test_build_explorer_prompt_human_assist_timing_rules():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "", max_human_assists=1)
    assert "no send_command budget left" in prompt
    assert "commands_remaining is still high enough" in prompt


def test_build_explorer_prompt_solo_tool_discipline_when_zero():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "", max_human_assists=0)
    assert "ask_human" not in prompt
    assert "Every turn MUST call send_command (or get_state)" in prompt
    assert "send_command, get_state, OR ask_human" not in prompt


def test_build_explorer_prompt_omits_human_assist_when_zero():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "", max_human_assists=0)
    assert "ask_human" not in prompt


def test_build_explorer_prompt_forbids_premature_success_in_thoughts():
    prompt = build_explorer_prompt("openai/gpt-4o-mini", "")
    assert "never declare \"SUCCESS\"" in prompt
    assert "non-null \"ending\"" in prompt
