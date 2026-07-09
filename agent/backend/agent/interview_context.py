"""Interview chat context budgeting and auto-summarization."""

from __future__ import annotations

from db.datetime_utils import utc_now

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from agent.memory_agent import build_llm
from agent.run_commands import command_lineage_run_ids_db, lineage_run_ids_db
from agent.run_messages import message_text
from db.models import ChatMessageRecord, RunRecord

SUMMARY_PREFIX = "[Interview summary — earlier messages compressed]\n\n"

# Fraction of model context used before compressing older chat turns.
COMPRESS_RATIO = 0.75
# User+assistant pairs to always keep verbatim at the tail.
KEEP_RECENT_PAIRS = 4

MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "google/gemini-2.5-flash": 1_000_000,
    "google/gemini-2.5-pro": 1_000_000,
    "google/gemini-2.0-flash": 1_000_000,
    "anthropic/claude": 200_000,
    "openai/gpt-4": 128_000,
}

DEFAULT_CONTEXT_LIMIT = 32_000


def estimate_tokens(text: str) -> int:
    """Rough token estimate (≈4 chars per token)."""
    return max(1, len(text) // 4)


def context_limit_for_model(model: str) -> int:
    lowered = model.lower()
    for prefix, limit in MODEL_CONTEXT_LIMITS.items():
        if prefix.lower() in lowered:
            return limit
    return DEFAULT_CONTEXT_LIMIT


def transcript_lineage_run_ids(db: Session, run: RunRecord) -> list[str]:
    """Root → current physical playthrough for step transcripts (stops at fresh attempts)."""
    return command_lineage_run_ids_db(db, run.id)


def chat_lineage_run_ids(db: Session, run: RunRecord) -> list[str]:
    """All runs in the episodic memory session — interview Q&A persists across attempts.

    Step transcripts use ``transcript_lineage_run_ids`` instead so New Attempt
    runs do not reload the parent run's raw step log into the LLM context.
    """
    session_id = run.memory_session_id
    if session_id:
        rows = (
            db.query(RunRecord.id)
            .filter(RunRecord.memory_session_id == session_id)
            .order_by(RunRecord.started_at)
            .all()
        )
        if rows:
            return [row.id for row in rows]
    return lineage_run_ids_db(db, run.id)


def load_chat_history(db: Session, run: RunRecord) -> list[ChatMessageRecord]:
    lineage = chat_lineage_run_ids(db, run)
    return (
        db.query(ChatMessageRecord)
        .filter(ChatMessageRecord.run_id.in_(lineage))
        .order_by(ChatMessageRecord.timestamp, ChatMessageRecord.id)
        .all()
    )


def _history_token_count(history: list[ChatMessageRecord], transcript: str, system_overhead: int) -> int:
    total = system_overhead + estimate_tokens(transcript)
    for msg in history:
        total += estimate_tokens(msg.content) + 4
    return total


async def maybe_compress_interview_history(
    db: Session,
    run: RunRecord,
    history: list[ChatMessageRecord],
    transcript: str,
    memory_model: str,
    *,
    pending_question: str,
) -> list[ChatMessageRecord]:
    """Summarize oldest chat turns when nearing the model context window."""
    if len(history) <= KEEP_RECENT_PAIRS * 2:
        return history

    limit = context_limit_for_model(run.explorer_model)
    system_overhead = estimate_tokens("x" * 8000)  # transcript + prompt shell reserve
    budget = int(limit * COMPRESS_RATIO)
    projected = _history_token_count(history, transcript, system_overhead) + estimate_tokens(
        pending_question
    )
    if projected <= budget:
        return history

    keep_count = KEEP_RECENT_PAIRS * 2
    to_summarize = history[:-keep_count] if len(history) > keep_count else []
    if not to_summarize:
        return history

    lines: list[str] = []
    for msg in to_summarize:
        speaker = "User" if msg.role == "user" else "Agent"
        lines.append(f"{speaker}: {msg.content}")
    conversation = "\n\n".join(lines)

    llm = build_llm(memory_model)
    summary_response = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    "Compress this post-run interview chat into concise bullet points. "
                    "Preserve puzzle clues, strategies, user instructions, and dead ends. "
                    "Do not invent facts."
                )
            ),
            HumanMessage(content=conversation),
        ]
    )
    summary_text = message_text(summary_response).strip()
    if not summary_text:
        return history

    for msg in to_summarize:
        db.delete(msg)

    summary_record = ChatMessageRecord(
        run_id=run.id,
        role="assistant",
        content=f"{SUMMARY_PREFIX}{summary_text}",
        timestamp=utc_now(),
    )
    db.add(summary_record)
    db.commit()
    db.refresh(summary_record)

    return load_chat_history(db, run)
