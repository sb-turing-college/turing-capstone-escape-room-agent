import type { GameState, RunResultInfo, RunSummary } from "../../types/agent";
import type { AgentStoreGet, AgentStoreSet } from "../agentStoreTypes";
import { resetReasoningCounter } from "./reasoningActions";

export const ACTIVE_RUN_STORAGE_KEY = "capstone_agent_active_run_id";

function persistActiveRunId(runId: string | null): void {
  if (typeof window === "undefined") return;
  if (runId) {
    window.localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, runId);
  } else {
    window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  }
}

export function createRunActions(set: AgentStoreSet, _get: AgentStoreGet) {
  return {
    setRunId: (runId: string | null) => {
      persistActiveRunId(runId);
      set({ runId });
    },

    setHydrationWatermark: (step: number | null) => set({ hydrationWatermark: step }),

    setLastRunResult: (result: RunResultInfo | null) => set({ lastRunResult: result }),

    setIsRunning: (value: boolean) => set({ isRunning: value }),

    setIsPaused: (value: boolean) => set({ isPaused: value }),

    setPauseContext: ({
      initiator,
      agentTheory = null,
      agentQuestion = null,
    }: {
      initiator: "human" | "agent" | null;
      agentTheory?: string | null;
      agentQuestion?: string | null;
    }) =>
      set({
        pauseInitiator: initiator,
        agentTheory,
        agentQuestion,
      }),

    setMaxHumanAssists: (value: number) =>
      set({ maxHumanAssists: Math.max(0, Math.min(3, value)) }),

    setModels: (models: string[], explorer: string, memory: string) =>
      set({
        models,
        defaultExplorerModel: explorer,
        defaultMemoryModel: memory,
        selectedModel: explorer,
      }),

    setSelectedModel: (model: string) => set({ selectedModel: model }),

    setMaxSteps: (steps: number) => set({ maxSteps: steps }),

    setLiveRunMaxSteps: (steps: number | null) => set({ liveRunMaxSteps: steps }),

    setGameState: (state: GameState) => set({ gameState: state }),

    setRuns: (runs: RunSummary[]) => set({ runs }),

    setStatusMessage: (msg: string) => set({ statusMessage: msg }),

    resetLiveState: () => {
      resetReasoningCounter();
      set({
        reasoningItems: [],
        mapNodes: [],
        mapEdges: [],
        gameState: null,
        memorySnippets: [],
        liveSteps: [],
        liveRunMaxSteps: null,
        lastEventAt: Date.now(),
        hydrationWatermark: null,
        lastRunResult: null,
        statusMessage: "Session Running",
        isPaused: false,
        pauseInitiator: null,
        agentTheory: null,
        agentQuestion: null,
      });
    },

    setPendingNewSession: (model: string) =>
      set({
        pendingNewSession: { model },
        selectedModel: model,
        analysisRunId: null,
        analysisDetail: null,
        analysisLoading: false,
        analysisError: null,
        activeMemorySessionId: null,
        memoryEntries: [],
        memoryCount: null,
      }),

    clearPendingNewSession: () => set({ pendingNewSession: null }),

    requestSessionsTab: () => set({ sessionsTabRequested: true }),

    clearSessionsTabRequest: () => set({ sessionsTabRequested: false }),

    setActiveMemorySessionId: (sessionId: string | null) =>
      set({ activeMemorySessionId: sessionId }),
  };
}
