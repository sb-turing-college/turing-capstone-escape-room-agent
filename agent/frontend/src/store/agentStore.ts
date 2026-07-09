import { create } from "zustand";

import { createAnalysisActions } from "./actions/analysisActions";
import { createMapActions } from "./actions/mapActions";
import { createMemoryActions } from "./actions/memoryActions";
import { createReasoningActions } from "./actions/reasoningActions";
import { ACTIVE_RUN_STORAGE_KEY, createRunActions } from "./actions/runActions";
import type { AgentStore } from "./agentStoreTypes";

export type { AgentStore } from "./agentStoreTypes";
export { ACTIVE_RUN_STORAGE_KEY };

export const useAgentStore = create<AgentStore>((set, get) => ({
  runId: null,
  isRunning: false,
  isPaused: false,
  pauseInitiator: null,
  agentTheory: null,
  agentQuestion: null,
  maxHumanAssists: 0,
  models: [],
  defaultExplorerModel: "",
  defaultMemoryModel: "",
  selectedModel: "",
  maxSteps: 50,
  liveRunMaxSteps: null,
  gameState: null,
  reasoningItems: [],
  mapNodes: [],
  mapEdges: [],
  runs: [],
  statusMessage: "Ready",
  memorySnippets: [],
  memoryCount: null,
  memoryEntries: [],
  liveSteps: [],
  lastEventAt: null,
  hydrationWatermark: null,
  analysisRunId: null,
  analysisDetail: null,
  analysisLoading: false,
  analysisError: null,
  lastRunResult: null,
  pendingNewSession: null,
  sessionsTabRequested: false,
  activeMemorySessionId: null,

  ...createRunActions(set, get),
  ...createReasoningActions(set, get),
  ...createMapActions(set, get),
  ...createMemoryActions(set),
  ...createAnalysisActions(set),
}));
