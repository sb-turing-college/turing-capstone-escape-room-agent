"""Post-run interview: chat with the model that played a run.

Uses the full SQL step transcript as context and a save_to_memory tool so
insights from the interview are available to future explorer runs via ChromaDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.memory_agent import MemoryAgent, build_llm
from agent.interview_context import transcript_lineage_run_ids
from agent.run_state_diff import MAP_REPLAY_STEP_TYPES
from db.models import ChatMessageRecord, RunRecord, StepRecord
from memory.chroma_store import ChromaStore

INTERVIEW_SYSTEM_PROMPT = """You are the AI agent that played "The Haunted Manor" text adventure in the run documented below.

The human is interviewing you about your decisions during that run. Answer based on the step log transcript — what you thought, tried, observed, and why you chose each action.

Rules:
- Ground answers in the transcript and the authoritative command index below — not in prior chat messages or memory notes.
- When asked how many commands or steps you took, use ONLY the send_command list below for the selected run. Never count steps from chat history, memory, or other runs.
- Only cite send_command actions that appear in the command index or transcript [action] send_command lines for the selected run.
- If the log does not show explicit reasoning for a step, say so honestly rather than inventing detailed intent you did not record.
- You may infer plausible motivations from observations and outcomes, but label inference as inference.
- Be concise unless asked for detail.
- Do not apologize excessively. Do not claim you had information that never appeared in the run log.
- This is a retrospective interview, not a new game session — do not issue game commands.
- When the human asks about hints they gave you, look for [human_hint] and [human_response] entries — not [memory_retrieved].

Authoritative command index (selected run — use for step/command counts):
{command_index}

Step log glossary (how to read [type] tags in the transcript):
- [human_hint]: A direct, proactive hint from the human observer watching the run.
- [human_response]: The human's answer to a question you asked via ask_human.
- [memory_retrieved]: Automatic recall from prior runs (ChromaDB). This is NOT a hint from the human in this session.
- [memory_stored]: Notes you saved to long-term memory during or after the run.
- [action] with ask_human: You paused and asked the human a specific question.
- [action] with send_command: A game command you executed.
- [thought]: Your recorded reasoning for a step.
- [system]: Run control events (pause, resume, limits). Resume lines may duplicate [human_hint]/[human_response] text.

Memory tool (save_to_memory):
- Treat save_to_memory as building a reusable playbook for future runs — not only dead ends or reflections.
- When you save an updated strategy that replaces an older agent_chat note, pass that note's doc id in
  supersedes so the old note is marked obsolete instead of accumulating duplicates.
- Active agent_chat notes for this session (doc id — preview):
{memory_index}
- Be proactive: if the human corrects a wrong assumption, reveals how an item or puzzle
  actually works, or gives a hint that would change your strategy in a future run, call
  save_to_memory in the same turn — do not wait to be asked.
- After a successful or near-complete run, proactively save confirmed solution paths as compact
  ordered command checklists (e.g. take X → use Y with Z → …) so the next run can execute them
  without rediscovery.
- Also save confirmed puzzle mechanics (e.g. an item is takeable despite misleading room text),
  concrete shortcuts, or dead ends you spot while reviewing the transcript.
- Use save_to_memory when the user explicitly asks you to remember something for future runs.
- Write clear, actionable notes in content (bullet points are fine). Summarize — do not paste
  the whole chat.
- After saving, tell the user briefly what you stored.
- Do not save vague praise, small talk, or information that adds nothing beyond the automatic
  run summary.

Run metadata:
- Model: {explorer_model}
- Success: {success}
- Steps: {steps_count}

Full run transcript:
{transcript}
"""


class SaveToMemoryInput(BaseModel):
    content: str = Field(
        description=(
            "Actionable note for future runs: strategy, puzzle solution, "
            "shortcut, item order, or dead end to avoid."
        ),
        min_length=1,
        max_length=4000,
    )
    reason: str = Field(
        description="Brief reason why this note will help in future runs.",
        min_length=1,
        max_length=500,
    )
    supersedes: list[str] = Field(
        default_factory=list,
        description=(
            "Optional doc ids of older agent_chat notes this note replaces "
            "(same memory session). Use when updating a playbook."
        ),
    )


@dataclass(frozen=True)
class InterviewReply:
    text: str
    memory_saved: bool


def filter_steps_for_transcript(steps: list[StepRecord], run: RunRecord) -> list[StepRecord]:
    """Drop map-replay noise; keep real gameplay and human-interaction steps."""
    seen_game_update = False
    filtered: list[StepRecord] = []
    for step in steps:
        if (step.extra or {}).get("replayed"):
            continue
        if run.continued_from_run_id and not run.is_fresh_attempt and not seen_game_update:
            if step.type in MAP_REPLAY_STEP_TYPES:
                continue
        if step.type == "game_update":
            seen_game_update = True
        filtered.append(step)
    return filtered


def format_step_line(step: StepRecord) -> str:
    room_part = f" ({step.room})" if step.room else ""
    return f"Step {step.step_number} [{step.type}]{room_part}: {step.content}"


def build_transcript(db: Session, run: RunRecord) -> str:
    """Build an untruncated transcript across the continue-run lineage."""
    lineage_ids = transcript_lineage_run_ids(db, run)
    runs_by_id = {
        record.id: record
        for record in db.query(RunRecord).filter(RunRecord.id.in_(lineage_ids)).all()
    }

    sections: list[str] = []
    for chain_run_id in lineage_ids:
        chain_run = runs_by_id.get(chain_run_id)
        if chain_run is None:
            continue
        steps = (
            db.query(StepRecord)
            .filter_by(run_id=chain_run_id)
            .order_by(StepRecord.step_number)
            .all()
        )
        filtered = filter_steps_for_transcript(steps, chain_run)
        if not filtered:
            continue
        header = f"=== Run {chain_run_id}"
        if chain_run.is_fresh_attempt and chain_run.continued_from_run_id:
            header += f" (new attempt from {chain_run.continued_from_run_id})"
        elif chain_run.continued_from_run_id:
            header += f" (continued from {chain_run.continued_from_run_id})"
        header += " ==="
        body = "\n".join(format_step_line(step) for step in filtered)
        sections.append(f"{header}\n{body}")

    return "\n\n".join(sections) if sections else "(No transcript steps recorded.)"


def extract_send_commands(db: Session, run: RunRecord) -> list[str]:
    """Ordered send_command strings for the selected run (transcript filters applied)."""
    steps = (
        db.query(StepRecord)
        .filter_by(run_id=run.id)
        .order_by(StepRecord.step_number)
        .all()
    )
    filtered = filter_steps_for_transcript(steps, run)
    prefix = "send_command:"
    commands: list[str] = []
    for step in filtered:
        if step.type == "action" and step.content.startswith(prefix):
            commands.append(step.content[len(prefix) :].strip())
    return commands


def format_command_index(run: RunRecord, commands: list[str]) -> str:
    """Authoritative send_command list for interview grounding."""
    if not commands:
        return f"Selected run id: {run.id}\nsend_command count: 0\n(No send_command actions recorded.)"
    lines = [
        f"Selected run id: {run.id}",
        f"send_command count: {len(commands)}",
        "Ordered commands:",
    ]
    lines.extend(f"  {index}. {command}" for index, command in enumerate(commands, start=1))
    return "\n".join(lines)


def format_memory_index(memory_agent: MemoryAgent, memory_session_id: str) -> str:
    """Active agent_chat doc ids so the model can supersede obsolete notes."""
    notes = memory_agent.list_active_interview_notes(memory_session_id)
    if not notes:
        return "(No active agent_chat memory notes for this session.)"
    lines = [
        "Active agent_chat notes (pass doc id in supersedes when replacing):",
    ]
    for entry in notes:
        doc_id = entry["id"]
        preview = (entry.get("document") or "").split("\n")[0][:120]
        lines.append(f"  - {doc_id}: {preview}")
    return "\n".join(lines)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
        return "\n".join(parts).strip()
    return str(content).strip() if content else ""


def _extract_reply(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _message_text(msg)
            if text:
                return text
    return ""


async def ask_about_run(
    run: RunRecord,
    transcript: str,
    history: list[ChatMessageRecord],
    question: str,
    store: ChromaStore,
    memory_model: str,
    db: Session,
) -> InterviewReply:
    """Ask the explorer model about its completed run; may save notes to memory."""
    memory_agent = MemoryAgent(store, memory_model)
    memory_session_id = run.memory_session_id or run.id
    saved_to_memory = False

    async def save_to_memory(
        content: str,
        reason: str,
        supersedes: list[str] | None = None,
    ) -> str:
        nonlocal saved_to_memory
        supersede_ids = [doc_id.strip() for doc_id in (supersedes or []) if doc_id.strip()]
        memory_agent.store_interview_note(
            run_id=run.id,
            memory_session_id=memory_session_id,
            content=content,
            reason=reason,
            supersedes=supersede_ids or None,
        )
        saved_to_memory = True
        if supersede_ids:
            return (
                f"Successfully saved to agent memory and marked {len(supersede_ids)} "
                "older note(s) as superseded."
            )
        return (
            "Successfully saved to agent memory. "
            "This note will be retrieved at the start of future runs."
        )

    save_tool = StructuredTool.from_function(
        coroutine=save_to_memory,
        name="save_to_memory",
        description=(
            "Save an actionable game insight to long-term memory (ChromaDB) as a next-run playbook. "
            "Call proactively for confirmed solution paths (ordered command checklists), corrected "
            "puzzle mechanics, or human hints — not only when explicitly asked. "
            "When replacing an older note, pass its doc id in supersedes. Keep notes concise."
        ),
        args_schema=SaveToMemoryInput,
    )

    commands = extract_send_commands(db, run)
    system = INTERVIEW_SYSTEM_PROMPT.format(
        explorer_model=run.explorer_model,
        success=run.success,
        steps_count=run.steps_count,
        transcript=transcript,
        command_index=format_command_index(run, commands),
        memory_index=format_memory_index(memory_agent, memory_session_id),
    )
    llm = build_llm(run.explorer_model)
    agent = create_react_agent(llm, [save_tool], prompt=system)

    messages: list[HumanMessage | AIMessage] = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=question))

    result = await agent.ainvoke({"messages": messages})
    reply = _extract_reply(result.get("messages", []))
    if not reply:
        reply = "I couldn't produce a reply. Please try rephrasing your question."
    return InterviewReply(text=reply, memory_saved=saved_to_memory)
