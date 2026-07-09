"""ChromaDB vector store for run summaries."""

from __future__ import annotations

from typing import Any

import chromadb


class ChromaStore:
    """Persistent vector store for run summaries and interview notes."""

    COLLECTION_NAME = "game_memory"

    def __init__(self, persist_dir: str) -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(self.COLLECTION_NAME)

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        """Semantic search over stored memory documents."""
        if self._collection.count() == 0:
            return []
        result = self._collection.query(query_texts=[query_text], n_results=min(n_results, self._collection.count()))
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [
            {"document": doc, "metadata": meta}
            for doc, meta in zip(documents, metadatas, strict=False)
        ]

    def add(self, doc_id: str, document: str, metadata: dict[str, Any]) -> None:
        self._collection.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])

    def get_entry(self, doc_id: str) -> dict[str, Any] | None:
        if self._collection.count() == 0:
            return None
        result = self._collection.get(ids=[doc_id], include=["documents", "metadatas"])
        ids = result.get("ids") or []
        if not ids:
            return None
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        return {
            "id": ids[0],
            "document": documents[0] if documents else "",
            "metadata": metadatas[0] if metadatas else {},
        }

    def mark_superseded(self, doc_id: str, superseded_by: str) -> bool:
        """Flag an entry as replaced by a newer memory note (metadata update only)."""
        entry = self.get_entry(doc_id)
        if entry is None:
            return False
        metadata = dict(entry.get("metadata") or {})
        metadata["superseded_by"] = superseded_by
        self._collection.update(
            ids=[doc_id],
            documents=[entry.get("document") or ""],
            metadatas=[metadata],
        )
        return True

    def clear(self) -> int:
        """Delete all stored memories. Returns the number of entries removed.

        This only wipes the agent's learned memory (ChromaDB) — it never
        touches the run/step history in the SQL database, which is a
        separate, permanent record only removed by the user directly.
        """
        removed = self._collection.count()
        if removed == 0:
            return 0
        existing = self._collection.get()
        ids = existing.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return removed

    def clear_matching(self, predicate) -> int:
        """Delete entries for which ``predicate(doc_id, metadata)`` is true."""
        if self._collection.count() == 0:
            return 0
        existing = self._collection.get(include=["metadatas"])
        ids = existing.get("ids", []) or []
        metadatas = existing.get("metadatas", []) or []
        to_delete = [
            doc_id
            for doc_id, metadata in zip(ids, metadatas, strict=False)
            if predicate(doc_id, metadata or {})
        ]
        if to_delete:
            self._collection.delete(ids=to_delete)
        return len(to_delete)

    def clear_session(self, memory_session_id: str, legacy_run_ids: set[str] | None = None) -> int:
        """Delete memories for one playthrough session only."""
        legacy_run_ids = legacy_run_ids or set()

        def matches(_doc_id: str, metadata: dict[str, Any]) -> bool:
            if metadata.get("memory_session_id") == memory_session_id:
                return True
            return (
                not metadata.get("memory_session_id")
                and metadata.get("run_id") in legacy_run_ids
            )

        return self.clear_matching(matches)

    @property
    def count(self) -> int:
        return self._collection.count()

    def list_entries(self) -> list[dict[str, Any]]:
        """Return all stored memory documents with metadata."""
        if self._collection.count() == 0:
            return []
        result = self._collection.get(include=["documents", "metadatas"])
        ids = result.get("ids", []) or []
        documents = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        entries: list[dict[str, Any]] = []
        for doc_id, document, metadata in zip(ids, documents, metadatas, strict=False):
            entries.append(
                {
                    "id": doc_id,
                    "document": document or "",
                    "metadata": metadata or {},
                }
            )
        entries.sort(
            key=lambda entry: (
                str((entry.get("metadata") or {}).get("created_at") or ""),
                str(entry.get("id") or ""),
            )
        )
        return entries
