import type { GameState, SaveActionResult, SaveSlotInfo } from "../types/game";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createGame(): Promise<GameState> {
  return request<GameState>("/game/new", { method: "POST" });
}

export function sendAction(sessionId: string, command: string): Promise<GameState> {
  return request<GameState>(`/game/${sessionId}/action`, {
    method: "POST",
    body: JSON.stringify({ command }),
  });
}

export function getGameState(sessionId: string): Promise<GameState> {
  return request<GameState>(`/game/${sessionId}/state`);
}

export function saveGame(
  sessionId: string,
  slot: number,
  clientId: string,
): Promise<SaveActionResult> {
  return request<SaveActionResult>(`/game/${sessionId}/save/${slot}`, {
    method: "POST",
    body: JSON.stringify({ client_id: clientId }),
  });
}

export function loadGame(
  sessionId: string,
  slot: number,
  clientId: string,
): Promise<GameState> {
  return request<GameState>(`/game/${sessionId}/load/${slot}`, {
    method: "POST",
    body: JSON.stringify({ client_id: clientId }),
  });
}

export function getSaveSlots(clientId: string): Promise<SaveSlotInfo[]> {
  return request<SaveSlotInfo[]>(`/game/saves?client_id=${encodeURIComponent(clientId)}`);
}
