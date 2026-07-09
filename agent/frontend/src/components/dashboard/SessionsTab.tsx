import { useMemo, useState } from "react";

import { fetchRunDetail } from "../../hooks/useAgentSocket";
import { useAgentStore } from "../../store/agentStore";
import { buildChartPoints } from "./SessionLearningCurve";
import { RunControlPanel } from "./RunControlPanel";
import { SessionManager } from "./SessionManager";

type SessionsTabProps = {
  onRunStarted: () => void;
};

export function SessionsTab({ onRunStarted }: SessionsTabProps) {
  const runs = useAgentStore((s) => s.runs);
  const selectAnalysisRun = useAgentStore((s) => s.selectAnalysisRun);

  const [hoveredRunId, setHoveredRunId] = useState<string | null>(null);
  const chartPoints = useMemo(() => buildChartPoints(runs), [runs]);

  const selectFinishedRun = (id: string) => {
    const run = runs.find((r) => r.run_id === id);
    if (!run || run.status === "running") return;
    selectAnalysisRun(id);
    void fetchRunDetail(id);
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto overscroll-y-contain lg:overflow-hidden">
      <div className="shrink-0">
        <RunControlPanel
          onRunStarted={onRunStarted}
          chartPoints={chartPoints}
          hoveredRunId={hoveredRunId}
          onHoverRunId={setHoveredRunId}
          onSelectRun={selectFinishedRun}
        />
      </div>
      <div className="min-h-0 lg:flex lg:flex-1 lg:flex-col">
        <SessionManager
          hoveredRunId={hoveredRunId}
          onHoverRunId={setHoveredRunId}
          onSelectFinishedRun={selectFinishedRun}
        />
      </div>
    </div>
  );
}
