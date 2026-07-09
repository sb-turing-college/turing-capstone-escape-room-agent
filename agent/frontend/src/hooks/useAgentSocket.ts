import { useEffect, useRef } from "react";

import { fetchRunDetail, fetchRuns } from "../api/agentApi";
import { resolveMemorySessionId } from "../lib/memorySession";
import { liveStepFromEvent, storedStepToEvent } from "../lib/stepLogUtils";
import { useAgentStore } from "../store/agentStore";
import type { AgentEvent, GameState, RunDetail } from "../types/agent";

export {
  clearMemory,
  continueRun,
  fetchMemoryCount,
  fetchMemoryEntries,
  fetchModels,
  fetchRunChat,
  fetchRunDetail,
  fetchRuns,
  fetchSpectateSession,
  pauseRun,
  resumeRun,
  retryRun,
  sendRunChatMessage,
  startRun,
  stopRun,
} from "../api/agentApi";
export type { SpectateSessionInfo } from "../api/agentApi";

export function applyGameUpdate(event: AgentEvent) {
  if (event.type !== "game_update" || !event.room) return;
  const state: GameState = {
    room: event.room,
    text: event.content ?? "",
    visible_items: event.visible_items ?? [],
    inventory: event.inventory ?? [],
    exits: event.exits ?? {},
    is_solved: event.is_solved ?? false,
    ending: event.ending ?? null,
  };
  useAgentStore.getState().setGameState(state);
}

export function hydrateFromRunDetail(detail: RunDetail) {
  const store = useAgentStore.getState();
  store.resetLiveState();

  let maxStep = 0;
  for (const stored of detail.steps) {
    const event = storedStepToEvent(stored);
    maxStep = Math.max(maxStep, stored.step_number);

    store.addReasoningEvent(event);
    store.addMapEvent(event);
    applyGameUpdate(event);

    const liveStep = liveStepFromEvent(event);
    if (liveStep) {
      store.addLiveStep(liveStep);
    }

    if (event.type === "memory_retrieved" || event.type === "memory_stored") {
      store.addMemorySnippet(event.content ?? "");
    }
  }

  store.setHydrationWatermark(maxStep);
  store.setStatusMessage(`Reconnected — replayed ${detail.steps.length} events`);
}

export function useAgentSocket(runId: string | null) {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/ws/${runId}`);
    socketRef.current = ws;

    ws.onmessage = (message) => {
      const event = JSON.parse(message.data) as AgentEvent;
      if (event.type === "ping") return;

      const store = useAgentStore.getState();
      if (
        typeof event.step === "number" &&
        store.hydrationWatermark !== null &&
        event.step <= store.hydrationWatermark
      ) {
        return;
      }
      store.touchLastEvent();
      store.addReasoningEvent(event);
      store.addMapEvent(event);
      applyGameUpdate(event);

      const liveStep = liveStepFromEvent(event);
      if (liveStep) {
        store.addLiveStep(liveStep);
      }

      if (event.type === "memory_retrieved" || event.type === "memory_stored") {
        store.addMemorySnippet(event.content ?? "");
        if (event.type === "memory_stored") {
          const sessionId =
            event.memory_session_id ??
            store.activeMemorySessionId ??
            resolveMemorySessionId(store.runs, runId, {
              activeSessionId: store.activeMemorySessionId,
            });
          if (sessionId) void store.refreshMemory(sessionId);
        }
      }
      if (event.type === "run_started") {
        if (typeof event.max_steps === "number") {
          store.setLiveRunMaxSteps(event.max_steps);
        }
        if (event.memory_session_id) {
          store.setActiveMemorySessionId(event.memory_session_id);
        }
      }
      if (event.type === "run_paused") {
        store.setIsPaused(true);
        store.setPauseContext({
          initiator: event.initiator ?? "human",
          agentTheory: event.agent_theory ?? null,
          agentQuestion: event.agent_question ?? null,
        });
        store.setStatusMessage(
          event.initiator === "agent"
            ? "Agent paused — waiting for your answer…"
            : "Paused — waiting for a hint…",
        );
      }
      if (event.type === "run_resumed") {
        store.setIsPaused(false);
        store.setPauseContext({ initiator: null });
        const response = event.human_response ?? event.hint;
        store.setStatusMessage(
          event.initiator === "agent"
            ? response
              ? `Resumed with your answer: ${response}`
              : "Resumed without your answer"
            : response
              ? `Resumed with hint: ${response}`
              : "Resumed without a hint",
        );
      }
      if (event.type === "run_complete") {
        store.setIsRunning(false);
        store.setIsPaused(false);
        const completedRunId = event.run_id ?? runId;
        const cmd = event.commands ?? event.steps ?? "?";
        store.setStatusMessage(
          event.success
            ? `Run complete (${cmd} commands)`
            : "Run finished without success",
        );
        if (event.memory_session_id) {
          store.setActiveMemorySessionId(event.memory_session_id);
          void store.refreshMemory(event.memory_session_id);
        }
        if (completedRunId) {
          store.selectAnalysisRun(completedRunId);
          void fetchRunDetail(completedRunId);
        }
        void fetchRuns();
      }
      if (event.type === "run_failed") {
        store.setIsRunning(false);
        store.setIsPaused(false);
        const failedRunId = event.run_id ?? runId;
        store.setStatusMessage(event.reason ?? "Run failed");
        if (event.memory_session_id) {
          store.setActiveMemorySessionId(event.memory_session_id);
          void store.refreshMemory(event.memory_session_id);
        }
        if (failedRunId) {
          store.selectAnalysisRun(failedRunId);
          void fetchRunDetail(failedRunId);
        }
        void fetchRuns();
      }
    };

    ws.onerror = () => {
      useAgentStore.getState().setStatusMessage("WebSocket error");
    };

    return () => {
      ws.close();
      socketRef.current = null;
    };
  }, [runId]);
}
