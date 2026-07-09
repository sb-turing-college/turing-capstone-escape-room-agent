import type { RunDetail } from "../../types/agent";
import type { AgentStoreSet } from "../agentStoreTypes";

export function createAnalysisActions(set: AgentStoreSet) {
  return {
    selectAnalysisRun: (runId: string) =>
      set({
        pendingNewSession: null,
        analysisRunId: runId,
        analysisDetail: null,
        analysisLoading: true,
        analysisError: null,
      }),

    setAnalysisDetail: (detail: RunDetail | null) =>
      set({ analysisDetail: detail, analysisLoading: false, analysisError: null }),

    setAnalysisLoading: (loading: boolean) => set({ analysisLoading: loading }),

    setAnalysisError: (error: string | null) =>
      set({ analysisError: error, analysisLoading: false }),

    clearAnalysis: () =>
      set({
        analysisRunId: null,
        analysisDetail: null,
        analysisLoading: false,
        analysisError: null,
      }),
  };
}
