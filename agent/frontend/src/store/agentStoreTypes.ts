import type { Edge, Node } from "@xyflow/react";

import type {
  AgentEvent,
  GameState,
  LiveStep,
  MemoryEntry,
  ReasoningItem,
  RunDetail,
  RunResultInfo,
  RunSummary,
} from "../types/agent";

export interface AgentStore {
  runId: string | null;
  isRunning: boolean;
  isPaused: boolean;
  pauseInitiator: "human" | "agent" | null;
  agentTheory: string | null;
  agentQuestion: string | null;
  maxHumanAssists: number;
  models: string[];
  defaultExplorerModel: string;
  defaultMemoryModel: string;
  selectedModel: string;
  maxSteps: number;
  /** send_command budget for the active live run (from run_started). */
  liveRunMaxSteps: number | null;
  gameState: GameState | null;
  reasoningItems: ReasoningItem[];
  mapNodes: Node[];
  mapEdges: Edge[];
  runs: RunSummary[];
  statusMessage: string;
  memorySnippets: string[];
  memoryCount: number | null;
  memoryEntries: MemoryEntry[];
  liveSteps: LiveStep[];
  lastEventAt: number | null;
  /** Highest step_number already rehydrated from the DB after a reconnect;
   *  used to drop duplicate WS backlog events with step <= watermark. */
  hydrationWatermark: number | null;
  analysisRunId: string | null;
  analysisDetail: RunDetail | null;
  analysisLoading: boolean;
  analysisError: string | null;
  /** Prominent end-of-run banner data; set on run_complete/run_failed. */
  lastRunResult: RunResultInfo | null;
  /** UI draft for a fresh session before the first run is started. */
  pendingNewSession: { model: string } | null;
  /** Optional hook to switch the dashboard to the Sessions tab (e.g. after Create new). */
  sessionsTabRequested: boolean;
  /** Episodic memory scope for the active / just-finished run (avoids UI race). */
  activeMemorySessionId: string | null;

  setRunId: (runId: string | null) => void;
  setHydrationWatermark: (step: number | null) => void;
  setLastRunResult: (result: RunResultInfo | null) => void;
  setIsRunning: (value: boolean) => void;
  setIsPaused: (value: boolean) => void;
  setPauseContext: (context: {
    initiator: "human" | "agent" | null;
    agentTheory?: string | null;
    agentQuestion?: string | null;
  }) => void;
  setMaxHumanAssists: (value: number) => void;
  setModels: (models: string[], explorer: string, memory: string) => void;
  setSelectedModel: (model: string) => void;
  setMaxSteps: (steps: number) => void;
  setLiveRunMaxSteps: (steps: number | null) => void;
  setGameState: (state: GameState) => void;
  addReasoningEvent: (event: AgentEvent) => void;
  addMapEvent: (event: AgentEvent) => void;
  setRuns: (runs: RunSummary[]) => void;
  setStatusMessage: (msg: string) => void;
  addMemorySnippet: (text: string) => void;
  clearMemorySnippets: () => void;
  refreshMemory: (memorySessionId?: string | null) => Promise<void>;
  addLiveStep: (step: LiveStep) => void;
  touchLastEvent: () => void;
  selectAnalysisRun: (runId: string) => void;
  setAnalysisDetail: (detail: RunDetail | null) => void;
  setAnalysisLoading: (loading: boolean) => void;
  setAnalysisError: (error: string | null) => void;
  clearAnalysis: () => void;
  resetLiveState: () => void;
  setPendingNewSession: (model: string) => void;
  clearPendingNewSession: () => void;
  requestSessionsTab: () => void;
  clearSessionsTabRequest: () => void;
  setActiveMemorySessionId: (sessionId: string | null) => void;
}

export type AgentStoreSet = (
  partial: Partial<AgentStore> | ((state: AgentStore) => Partial<AgentStore>),
) => void;
export type AgentStoreGet = () => AgentStore;
