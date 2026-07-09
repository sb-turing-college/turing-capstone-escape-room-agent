import { useEffect, useState } from "react";

import { DisclaimerGate } from "./components/DisclaimerGate";
import { DashboardTabId, DashboardTabs } from "./components/dashboard/DashboardTabs";
import { LiveTab } from "./components/dashboard/LiveTab";
import { ReviewTab } from "./components/dashboard/ReviewTab";
import { SessionsTab } from "./components/dashboard/SessionsTab";
import {
  fetchModels,
  fetchRunDetail,
  fetchRuns,
  hydrateFromRunDetail,
  useAgentSocket,
} from "./hooks/useAgentSocket";
import { ACTIVE_RUN_STORAGE_KEY, useAgentStore } from "./store/agentStore";

function RunStatusPill() {
  const statusMessage = useAgentStore((s) => s.statusMessage);
  if (!statusMessage || statusMessage === "Ready") return null;
  return (
    <span className="rounded bg-gray-800/80 px-2 py-0.5 text-[10px] text-gray-300">
      {statusMessage}
    </span>
  );
}

export default function App() {
  const runId = useAgentStore((s) => s.runId);
  const sessionsTabRequested = useAgentStore((s) => s.sessionsTabRequested);
  useAgentSocket(runId);
  const [activeTab, setActiveTab] = useState<DashboardTabId>("sessions");

  useEffect(() => {
    if (!sessionsTabRequested) return;
    setActiveTab("sessions");
    useAgentStore.getState().clearSessionsTabRequest();
  }, [sessionsTabRequested]);

  useEffect(() => {
    async function init() {
      await Promise.all([fetchModels(), fetchRuns()]);

      const savedRunId = window.localStorage.getItem(ACTIVE_RUN_STORAGE_KEY);
      if (!savedRunId) return;

      const store = useAgentStore.getState();
      try {
        const detail = await fetchRunDetail(savedRunId);
        if (detail.status === "running") {
          hydrateFromRunDetail(detail);
          store.setRunId(savedRunId);
          store.setIsRunning(true);
          setActiveTab("live");
        } else {
          window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
          store.selectAnalysisRun(savedRunId);
          setActiveTab("sessions");
        }
      } catch {
        window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
      }
    }
    void init();
  }, []);

  return (
    <DisclaimerGate>
      <div className="flex h-dvh flex-col overflow-hidden">
      <header className="shrink-0 border-b border-gray-800/60 bg-[#0b0714]/95 px-4 py-3 backdrop-blur-md md:px-6">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <h1 className="shrink-0 text-lg font-bold text-white">Escape Room Agent</h1>

          <DashboardTabs
            variant="header"
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />

          <div className="flex flex-wrap items-center justify-end gap-2 lg:min-w-[12rem]">
            <RunStatusPill />
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-4 md:p-6">
        <div
          className={
            activeTab === "sessions"
              ? "flex min-h-0 flex-1 flex-col"
              : "hidden"
          }
        >
          <SessionsTab onRunStarted={() => setActiveTab("live")} />
        </div>
        <div
          className={
            activeTab === "live" ? "flex min-h-0 flex-1 flex-col" : "hidden"
          }
        >
          <LiveTab />
        </div>
        <div
          className={
            activeTab === "review" ? "flex min-h-0 flex-1 flex-col" : "hidden"
          }
        >
          <ReviewTab />
        </div>
      </main>
      </div>
    </DisclaimerGate>
  );
}
