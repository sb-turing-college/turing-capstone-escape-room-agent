"""Memory agent: ChromaDB retrieval + run summary storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langchain_openai import ChatOpenAI

from agent.memory_sources import (
    AGENT_CHAT,
    FALLBACK_SUMMARY,
    IN_GAME_REFLECTION,
    is_agent_chat_source,
)
from agent.run_memory import (
    compose_run_memory_document,
    extract_final_reflection,
    format_state_footer,
    reflection_usable,
    replace_state_footer_for_fresh_attempt,
)
from agent.run_messages import message_text
from config import get_settings
from memory.chroma_store import ChromaStore

MAX_RUN_SUMMARIES = 2
RUN_SUMMARY_MAX_TOKENS = 1024

RUN_SUMMARY_PROMPT = """Summarize this text-adventure agent run in 5-8 complete bullet points.
Focus on puzzle clues, dead ends, red herrings, and what worked.

Output rules (critical):
- Bullet points only — no title, no introduction, no "Here's a summary"
- Every bullet must be a complete sentence
- Do not stop mid-bullet

Success: {success}
Model: {explorer_model}

{condensed}
"""


def build_llm(
    model: str,
    *,
    temperature: float = 0.1,
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
    exclude_reasoning: bool = False,
) -> ChatOpenAI:
    """Build an OpenRouter-backed chat model.

    `reasoning_effort` requests OpenRouter's unified `reasoning` field
    (e.g. "low"/"medium"/"high"). Per OpenRouter docs, models that don't
    support reasoning simply omit the field server-side, so it's safe to
    pass for any model — but we only opt in explicitly (see explorer.py)
    since it adds latency/cost for models that do support it.

    `exclude_reasoning` keeps reasoning internal so completion budget is
    not eaten before visible summary text (memory summarization).
    """
    settings = get_settings()
    extra_body: dict[str, Any] | None = None
    if reasoning_effort:
        extra_body = {"reasoning": {"effort": reasoning_effort}}
    elif exclude_reasoning:
        extra_body = {"reasoning": {"exclude": True}}

    kwargs: dict[str, Any] = {
        "model": model,
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": str(settings["openrouter_api_key"]),
        "temperature": temperature,
        "extra_body": extra_body,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


class MemoryAgent:
    """Retrieve ChromaDB context for the explorer and store run summaries."""

    QUERY = "What have I learned playing The Haunted Manor text adventure?"

    def __init__(self, store: ChromaStore, memory_model: str) -> None:
        self.store = store
        self.llm = build_llm(
            memory_model,
            max_tokens=RUN_SUMMARY_MAX_TOKENS,
            exclude_reasoning=True,
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
        metadata = entry.get("metadata") or {}
        created_at = str(metadata.get("created_at") or "")
        entry_id = str(entry.get("id") or metadata.get("run_id") or "")
        return created_at, entry_id

    @staticmethod
    def _is_superseded(metadata: dict[str, Any]) -> bool:
        return bool(metadata.get("superseded_by"))

    @staticmethod
    def _is_interview_entry(metadata: dict[str, Any]) -> bool:
        return is_agent_chat_source(metadata.get("source"))

    @staticmethod
    def _session_entries(
        all_entries: list[dict[str, Any]], memory_session_id: str
    ) -> list[dict[str, Any]]:
        return [
            entry
            for entry in all_entries
            if (entry.get("metadata") or {}).get("memory_session_id") == memory_session_id
        ]

    @staticmethod
    def _format_context(
        interview_hits: list[dict[str, Any]],
        summary_hits: list[dict[str, Any]],
    ) -> str:
        sections: list[str] = []

        sections.append("Player instructions (agent chat — chronological, oldest first):")
        if interview_hits:
            sections.extend(hit.get("document", "") for hit in interview_hits if hit.get("document"))
        else:
            sections.append("None.")

        sections.append("")
        sections.append("Past run summaries (background only, chronological — never override player instructions):")
        if summary_hits:
            sections.extend(hit.get("document", "") for hit in summary_hits if hit.get("document"))
        else:
            sections.append("None.")

        return "\n".join(sections)

    def get_context(
        self,
        memory_session_id: str,
        *,
        fresh_attempt: bool = False,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Build prompt context scoped to one playthrough (memory session)."""
        all_entries = self.store.list_entries()
        session_entries = self._session_entries(all_entries, memory_session_id)
        if not session_entries:
            return "", []

        entry_index = {entry["id"]: index for index, entry in enumerate(session_entries)}
        interview_entries: list[dict[str, Any]] = []
        for entry in session_entries:
            metadata = entry.get("metadata") or {}
            if not self._is_interview_entry(metadata):
                continue
            if self._is_superseded(metadata):
                continue
            interview_entries.append(
                {
                    "id": entry["id"],
                    "document": entry["document"],
                    "metadata": metadata,
                    "_index": entry_index.get(entry["id"], 0),
                }
            )

        interview_entries.sort(
            key=lambda entry: (
                self._entry_sort_key(entry)[0],
                entry.get("_index", 0),
            ),
        )
        for entry in interview_entries:
            entry.pop("_index", None)

        summary_candidates = [
            {
                "id": entry["id"],
                "document": entry["document"],
                "metadata": entry.get("metadata") or {},
            }
            for entry in session_entries
            if not self._is_interview_entry(entry.get("metadata") or {})
            and not self._is_superseded(entry.get("metadata") or {})
        ]
        summary_candidates.sort(key=self._entry_sort_key)
        summary_hits = summary_candidates[-MAX_RUN_SUMMARIES:]

        if fresh_attempt:
            for hit in summary_hits:
                document = hit.get("document", "")
                if document:
                    hit["document"] = replace_state_footer_for_fresh_attempt(document)

        hits = interview_entries + summary_hits
        context = self._format_context(interview_entries, summary_hits)
        return context, hits

    async def store_run_summary(
        self,
        run_id: str,
        steps: list[dict[str, Any]],
        success: bool,
        explorer_model: str,
        memory_session_id: str,
        *,
        last_state: dict[str, Any] | None = None,
        commands_used: int = 0,
        max_commands: int = 50,
    ) -> tuple[str, str]:
        """Persist run memory: agent reflection + footer, or LLM summary fallback.

        Returns ``(document, source)`` where source is ``in_game_reflection`` or
        ``fallback_summary``.
        """
        footer = format_state_footer(
            last_state,
            success=success,
            commands_used=commands_used,
            max_commands=max_commands,
        )
        reflection = extract_final_reflection(steps)
        if reflection_usable(reflection):
            document = compose_run_memory_document(reflection or "", footer)
            source = IN_GAME_REFLECTION
        else:
            document = await self._llm_run_summary(
                steps, success, explorer_model
            )
            document = compose_run_memory_document(document, footer)
            source = FALLBACK_SUMMARY

        self.store.add(
            doc_id=run_id,
            document=document,
            metadata={
                "source": source,
                "run_id": run_id,
                "memory_session_id": memory_session_id,
                "success": success,
                "explorer_model": explorer_model,
                "steps_count": len(steps),
                "created_at": self._utc_now_iso(),
            },
        )
        return document, source

    async def _llm_run_summary(
        self,
        steps: list[dict[str, Any]],
        success: bool,
        explorer_model: str,
    ) -> str:
        """LLM fallback when the explorer did not emit a usable closing thought."""
        condensed = "\n".join(
            f"[{s.get('type')}] {s.get('content', '')[:300]}"
            for s in steps[-40:]
        )
        prompt = RUN_SUMMARY_PROMPT.format(
            success=success,
            explorer_model=explorer_model,
            condensed=condensed,
        )
        response = await self.llm.ainvoke(prompt)
        summary = message_text(response).strip()
        if not summary:
            raise RuntimeError("Run summary LLM returned empty text")
        return summary

    def list_active_interview_notes(
        self, memory_session_id: str
    ) -> list[dict[str, Any]]:
        """Non-superseded agent_chat entries for the memory session (oldest first)."""
        entries = [
            entry
            for entry in self._session_entries(self.store.list_entries(), memory_session_id)
            if self._is_interview_entry(entry.get("metadata") or {})
            and not self._is_superseded(entry.get("metadata") or {})
        ]
        entries.sort(key=self._entry_sort_key)
        return entries

    def supersede_interview_notes(
        self,
        *,
        doc_ids: list[str],
        superseded_by: str,
        memory_session_id: str,
    ) -> list[str]:
        """Mark older agent_chat notes as superseded. Returns ids actually updated."""
        updated: list[str] = []
        for doc_id in doc_ids:
            entry = self.store.get_entry(doc_id)
            if entry is None:
                continue
            metadata = entry.get("metadata") or {}
            if metadata.get("memory_session_id") != memory_session_id:
                continue
            if not self._is_interview_entry(metadata):
                continue
            if self._is_superseded(metadata):
                continue
            if self.store.mark_superseded(doc_id, superseded_by):
                updated.append(doc_id)
        return updated

    def store_interview_note(
        self,
        *,
        run_id: str,
        memory_session_id: str,
        content: str,
        reason: str,
        supersedes: list[str] | None = None,
    ) -> str:
        """Persist a manual note from post-run interview chat for future runs."""
        note = content.strip()
        if not note:
            raise ValueError("content must not be empty")
        doc_id = f"interview-{run_id}-{uuid4()}"
        document = f"{note}\n(Interview note: {reason.strip()})"
        self.store.add(
            doc_id=doc_id,
            document=document,
            metadata={
                "source": AGENT_CHAT,
                "run_id": run_id,
                "memory_session_id": memory_session_id,
                "reason": reason.strip()[:500],
                "created_at": self._utc_now_iso(),
            },
        )
        if supersedes:
            self.supersede_interview_notes(
                doc_ids=supersedes,
                superseded_by=doc_id,
                memory_session_id=memory_session_id,
            )
        return doc_id
