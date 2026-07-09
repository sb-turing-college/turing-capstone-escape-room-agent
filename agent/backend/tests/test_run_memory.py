"""Tests for run memory document helpers (B+ reflection + footer)."""

from __future__ import annotations

from agent.run_memory import (
    REFLECTION_MIN_CHARS,
    compose_run_memory_document,
    extract_final_reflection,
    format_state_footer,
    reflection_usable,
    replace_state_footer_for_fresh_attempt,
)


def test_extract_final_reflection_returns_last_thought():
    steps = [
        {"type": "thought", "content": "First idea."},
        {"type": "action", "content": "send_command: look around"},
        {"type": "thought", "content": "Progress summary with enough detail to pass the minimum length threshold for reflection usability checks."},
    ]
    assert extract_final_reflection(steps) == steps[-1]["content"]


def test_reflection_usable_accepts_short_but_meaningful_failure():
    assert reflection_usable("Still no idea how to open the grate after trying both codes and the hook interaction.")
    assert not reflection_usable("Too short.")
    assert len("Still no idea how to open the grate after trying both codes and the hook interaction.") >= REFLECTION_MIN_CHARS


def test_format_state_footer_uses_key_value_lines():
    footer = format_state_footer(
        {
            "room": "parlor",
            "inventory": ["rope", "small_key"],
            "visible_items": ["grate"],
            "ending": None,
        },
        success=False,
        commands_used=20,
        max_commands=20,
    )
    assert "Ground truth (game state at run end):" in footer
    assert "room: parlor" in footer
    assert "inventory: rope, small_key" in footer
    assert "commands_used: 20/20" in footer
    assert "ending: none" in footer


def test_compose_run_memory_document_separates_reflection_and_footer():
    doc = compose_run_memory_document(
        "Agent reflection text.",
        "footer line",
    )
    assert doc.startswith("Agent reflection text.")
    assert doc.endswith("footer line")


def test_replace_state_footer_for_fresh_attempt():
    footer = format_state_footer(
        {"room": "lords_office", "inventory": ["brass key"], "ending": None},
        success=False,
        commands_used=20,
        max_commands=25,
    )
    doc = compose_run_memory_document("Learned the safe code pattern.", footer)
    replaced = replace_state_footer_for_fresh_attempt(doc)

    assert "Ground truth (game state at run end):" not in replaced
    assert "inventory: brass key" not in replaced
    assert "Learned the safe code pattern." in replaced
    assert (
        "[Prior attempt ended at room 'lords_office' with ending 'none' "
        "after 20/25 commands. Simulation is now reset.]"
    ) in replaced
