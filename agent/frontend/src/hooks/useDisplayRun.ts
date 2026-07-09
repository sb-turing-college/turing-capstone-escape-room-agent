import { useMemo } from "react";

import {
  gameStateFromSteps,
  liveStepsFromStored,
  mapGraphFromSteps,
  reasoningItemsFromSteps,
} from "../lib/stepLogUtils";
import { useAgentStore } from "../store/agentStore";
import type { GameState, LiveStep } from "../types/agent";

export function useDisplayRun() {
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const analysisDetail = useAgentStore((s) => s.analysisDetail);
  const liveSteps = useAgentStore((s) => s.liveSteps);
  const reasoningItems = useAgentStore((s) => s.reasoningItems);
  const mapNodes = useAgentStore((s) => s.mapNodes);
  const mapEdges = useAgentStore((s) => s.mapEdges);
  const gameState = useAgentStore((s) => s.gameState);
  const runId = useAgentStore((s) => s.runId);
  const isRunning = useAgentStore((s) => s.isRunning);

  // While a run is live, always show WS-driven state — even if analysisRunId
  // is still set from Review (e.g. after "Continue Run").
  const isReplayMode = Boolean(analysisRunId != null && !(isRunning && runId != null));

  const focusedRunId = isReplayMode ? analysisRunId : runId;

  const displaySteps: LiveStep[] = useMemo(() => {
    if (isReplayMode && analysisDetail) {
      return liveStepsFromStored(analysisDetail.steps);
    }
    return liveSteps;
  }, [isReplayMode, analysisDetail, liveSteps]);

  const reasoningItemsDisplay = useMemo(() => {
    if (isReplayMode && analysisDetail) {
      return reasoningItemsFromSteps(analysisDetail.steps);
    }
    return reasoningItems;
  }, [isReplayMode, analysisDetail, reasoningItems]);

  const mapGraph = useMemo(() => {
    if (isReplayMode && analysisDetail) {
      return mapGraphFromSteps(analysisDetail.steps);
    }
    return { nodes: mapNodes, edges: mapEdges };
  }, [isReplayMode, analysisDetail, mapNodes, mapEdges]);

  const displayGameState: GameState | null = useMemo(() => {
    if (isReplayMode && analysisDetail) {
      return gameStateFromSteps(analysisDetail.steps);
    }
    return gameState;
  }, [isReplayMode, analysisDetail, gameState]);

  return {
    isReplayMode,
    focusedRunId,
    isRunning: isReplayMode ? analysisDetail?.status === "running" : isRunning,
    displaySteps,
    reasoningItems: reasoningItemsDisplay,
    mapGraph,
    displayGameState,
    analysisDetail,
  };
}
