"""Thin async HTTP client for the capstone-game REST API."""

from __future__ import annotations

from typing import Any

import httpx


class GameClient:
    """Async HTTP client for the capstone-game REST API (contract-validated)."""

    EXPECTED_FIELDS = {
        "session_id",
        "text",
        "room",
        "visible_items",
        "exits",
        "inventory",
        "is_solved",
        "object_states",
        "available_verbs",
        "image",
        "ending",
    }

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def validate_response(data: dict[str, Any]) -> dict[str, Any]:
        """Ensure the game API response matches the expected field set."""
        missing = GameClient.EXPECTED_FIELDS - set(data.keys())
        extra = set(data.keys()) - GameClient.EXPECTED_FIELDS
        if missing or extra:
            raise ValueError(
                f"Game API contract drift: missing={sorted(missing)} extra={sorted(extra)}"
            )
        return data

    async def new_game(self) -> dict[str, Any]:
        """Start a new game session and store ``session_id`` on this client."""
        response = await self._client.post(f"{self.base_url}/game/new")
        response.raise_for_status()
        data = self.validate_response(response.json())
        self.session_id = data["session_id"]
        return data

    async def send_command(self, command: str) -> dict[str, Any]:
        """Send a text command to the active session."""
        if not self.session_id:
            raise RuntimeError("No active game session. Call new_game() first.")
        response = await self._client.post(
            f"{self.base_url}/game/{self.session_id}/action",
            json={"command": command},
        )
        response.raise_for_status()
        return self.validate_response(response.json())

    async def get_state(self) -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("No active game session. Call new_game() first.")
        response = await self._client.get(f"{self.base_url}/game/{self.session_id}/state")
        response.raise_for_status()
        return self.validate_response(response.json())

    async def export_state(self) -> dict[str, Any]:
        """Export raw ``GameState.to_dict()`` for the active session."""
        if not self.session_id:
            raise RuntimeError("No active game session. Call new_game() first.")
        response = await self._client.get(
            f"{self.base_url}/game/{self.session_id}/export-state"
        )
        response.raise_for_status()
        return response.json()

    async def restore_state(self, state: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            f"{self.base_url}/game/restore",
            json={"state": state},
        )
        response.raise_for_status()
        data = self.validate_response(response.json())
        self.session_id = data["session_id"]
        return data

    async def restore_session(
        self,
        *,
        session_id: str | None = None,
        game_state_json: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Restore a game session from a live id or exported snapshot.

        Returns ``(state, restored_from_snapshot)``. Tries ``session_id`` first;
        falls back to ``game_state_json`` when the live session is gone.
        """
        if session_id:
            self.session_id = session_id
            try:
                return await self.get_state(), False
            except httpx.HTTPError:
                pass

        if game_state_json:
            restored = await self.restore_state(game_state_json)
            return restored, True

        raise RuntimeError("No session_id or game_state_json available to restore.")

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
