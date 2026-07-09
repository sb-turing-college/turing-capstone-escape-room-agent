import { useAgentStore } from "../store/agentStore";
import type { ChatMessage, ChatResponse, MemoryEntry, RunDetail } from "../types/agent";

const API_BASE = "/api";

export async function fetchDisclaimerStatus(): Promise<{ accepted: boolean }> {
  const res = await fetch(`${API_BASE}/agent/disclaimer/status`);
  if (!res.ok) throw new Error("Failed to load disclaimer status");
  return res.json() as Promise<{ accepted: boolean }>;
}

export async function acceptDisclaimer(): Promise<void> {
  const res = await fetch(`${API_BASE}/agent/disclaimer/accept`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to accept disclaimer");
  }
}

export async function fetchModels() {
  const res = await fetch(`${API_BASE}/agent/models`);
  if (!res.ok) throw new Error("Failed to load models");
  const data = await res.json();
  useAgentStore.getState().setModels(
    data.models,
    data.default_explorer_model,
    data.default_memory_model,
  );
}

export async function fetchRuns() {
  const res = await fetch(`${API_BASE}/agent/runs`);
  if (!res.ok) throw new Error("Failed to load runs");
  const data = await res.json();
  useAgentStore.getState().setRuns(data);
}

export interface SpectateSessionInfo {
  session_id: string | null;
  restored: boolean;
  pending: boolean;
}

export async function fetchSpectateSession(runId: string): Promise<SpectateSessionInfo> {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/spectate-session`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to load spectate session");
  }
  return res.json() as Promise<SpectateSessionInfo>;
}

export async function fetchRunDetail(runId: string) {
  useAgentStore.getState().setAnalysisLoading(true);
  try {
    const res = await fetch(`${API_BASE}/agent/run/${runId}`);
    if (!res.ok) throw new Error("Failed to load run detail");
    const data = (await res.json()) as RunDetail;
    useAgentStore.getState().setAnalysisDetail(data);
    return data;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load run";
    useAgentStore.getState().setAnalysisError(message);
    throw err;
  }
}

export async function fetchRunChat(runId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/chat`);
  if (!res.ok) throw new Error("Failed to load interview chat");
  return res.json() as Promise<ChatMessage[]>;
}

export async function sendRunChatMessage(
  runId: string,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to send message");
  }
  return res.json() as Promise<ChatResponse>;
}

export async function startRun(
  explorerModel: string,
  maxSteps: number,
  inheritMemorySessionId?: string | null,
  maxHumanAssists = 0,
  hint?: string | null,
) {
  const body: Record<string, unknown> = {
    explorer_model: explorerModel,
    max_steps: maxSteps,
    max_human_assists: maxHumanAssists,
  };
  if (inheritMemorySessionId) {
    body.inherit_memory_session_id = inheritMemorySessionId;
  }
  const hintText = hint?.trim();
  if (hintText) {
    body.hint = hintText;
  }
  const res = await fetch(`${API_BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to start run");
  }
  return res.json() as Promise<{ run_id: string }>;
}

export async function stopRun(runId: string) {
  await fetch(`${API_BASE}/agent/stop/${runId}`, { method: "POST" });
}

export async function pauseRun(runId: string) {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/pause`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to pause run");
  }
}

export async function resumeRun(runId: string, humanResponse: string | null) {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ human_response: humanResponse }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to resume run");
  }
}

export async function continueRun(
  runId: string,
  options: { hint?: string | null; maxSteps?: number; maxHumanAssists?: number } = {},
): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/continue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hint: options.hint ?? null,
      max_steps: options.maxSteps ?? null,
      max_human_assists: options.maxHumanAssists ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to continue run");
  }
  return res.json() as Promise<{ run_id: string }>;
}

export async function retryRun(
  runId: string,
  options: { hint?: string | null; maxSteps?: number; maxHumanAssists?: number } = {},
): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/agent/run/${runId}/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hint: options.hint ?? null,
      max_steps: options.maxSteps ?? null,
      max_human_assists: options.maxHumanAssists ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to start new attempt");
  }
  return res.json() as Promise<{ run_id: string }>;
}

export async function fetchMemoryCount(memorySessionId?: string): Promise<number> {
  const query = memorySessionId
    ? `?memory_session_id=${encodeURIComponent(memorySessionId)}`
    : "";
  const res = await fetch(`${API_BASE}/agent/memory/count${query}`);
  if (!res.ok) throw new Error("Failed to load memory count");
  const data = await res.json();
  return data.count as number;
}

export async function fetchMemoryEntries(memorySessionId?: string): Promise<MemoryEntry[]> {
  const query = memorySessionId
    ? `?memory_session_id=${encodeURIComponent(memorySessionId)}`
    : "";
  const res = await fetch(`${API_BASE}/agent/memory${query}`);
  if (!res.ok) throw new Error("Failed to load memory entries");
  return res.json() as Promise<MemoryEntry[]>;
}

export async function clearMemory(memorySessionId?: string): Promise<{ removed: number }> {
  const res = await fetch(`${API_BASE}/agent/memory/clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      memorySessionId ? { memory_session_id: memorySessionId } : {},
    ),
  });
  if (!res.ok) throw new Error("Failed to clear memory");
  return res.json();
}
