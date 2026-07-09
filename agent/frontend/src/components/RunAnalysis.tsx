import { useEffect, useMemo, useState } from "react";

import { fetchRunDetail } from "../hooks/useAgentSocket";
import {
  filterStoredSteps,
  formatRunDuration,
  liveStepFromStored,
  stepTypeCounts,
  type StepFilter,
} from "../lib/stepLogUtils";
import { useAgentStore } from "../store/agentStore";
import type { LiveStep } from "../types/agent";
import { StepLogList } from "./StepLogList";

const FILTERS: { id: StepFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "gameplay", label: "Gameplay" },
  { id: "commands", label: "Commands" },
  { id: "thoughts", label: "Thoughts" },
  { id: "map", label: "Map" },
  { id: "memory", label: "Memory" },
  { id: "blocked", label: "Blocked" },
];

const panelClass =
  "flex h-full min-h-0 flex-col rounded-lg border border-purple-900/40 bg-panel/80 p-4";

export function RunAnalysis() {
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const analysisDetail = useAgentStore((s) => s.analysisDetail);
  const analysisLoading = useAgentStore((s) => s.analysisLoading);
  const analysisError = useAgentStore((s) => s.analysisError);
  const [filter, setFilter] = useState<StepFilter>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!analysisRunId) return;
    void fetchRunDetail(analysisRunId);
  }, [analysisRunId]);

  const counts = useMemo(
    () => (analysisDetail ? stepTypeCounts(analysisDetail.steps) : {}),
    [analysisDetail],
  );

  const displaySteps: LiveStep[] = useMemo(() => {
    if (!analysisDetail) return [];
    const filtered = filterStoredSteps(analysisDetail.steps, filter);
    const needle = search.trim().toLowerCase();
    return filtered
      .map((s) => liveStepFromStored(s))
      .filter((s): s is LiveStep => s != null)
      .filter(
        (s) =>
          !needle ||
          s.content.toLowerCase().includes(needle) ||
          (s.room?.toLowerCase().includes(needle) ?? false),
      );
  }, [analysisDetail, filter, search]);

  if (!analysisRunId) {
    return (
      <div className={panelClass}>
        <h2 className="shrink-0 text-sm font-semibold text-accent">Agent Logs</h2>
        <p className="mt-2 text-xs text-gray-500">
          Select a finished run in Sessions to inspect its event timeline and stats.
        </p>
      </div>
    );
  }

  return (
    <div className={panelClass}>
      <h2 className="mb-2 shrink-0 text-sm font-semibold text-accent">Agent Logs</h2>

      {analysisLoading && !analysisDetail && (
        <p className="shrink-0 text-xs text-gray-400">Loading run…</p>
      )}

      {analysisError && <p className="mb-2 shrink-0 text-xs text-red-300">{analysisError}</p>}

      {analysisDetail && (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-3 shrink-0 overflow-x-auto">
            <div className="grid min-w-[34rem] grid-cols-9 gap-1 text-[9px]">
              <Stat label="Status" value={analysisDetail.status} />
              <Stat
                label="Result"
                value={
                  analysisDetail.success === true
                    ? "Success"
                    : analysisDetail.success === false
                      ? "Failed"
                      : "—"
                }
              />
              <Stat label="Model" value={analysisDetail.explorer_model.split("/").pop() ?? ""} />
              <Stat
                label="Duration"
                value={formatRunDuration(analysisDetail.started_at, analysisDetail.finished_at)}
              />
              <Stat label="Events" value={String(analysisDetail.steps.length)} />
              <Stat label="Commands" value={String(counts.action ?? 0)} />
              <Stat
                label="Thoughts"
                value={String((counts.thought ?? 0) + (counts.thinking ?? 0))}
              />
              <Stat
                label="Memory"
                value={String((counts.memory_retrieved ?? 0) + (counts.memory_stored ?? 0))}
              />
              <Stat label="Blocked" value={String(counts.blocked ?? 0)} />
            </div>
          </div>

          {analysisDetail.error_message && (
            <p className="mb-3 shrink-0 rounded border border-red-500/40 bg-red-950/30 p-2 text-xs text-red-200">
              {analysisDetail.error_message}
            </p>
          )}

          <div className="mb-2 flex shrink-0 flex-wrap items-center gap-1">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`rounded px-2 py-1 text-[10px] ${
                  filter === f.id
                    ? "bg-accent text-white"
                    : "border border-gray-700 text-gray-400 hover:text-white"
                }`}
                onClick={() => setFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
            <span className="mx-1 text-[10px] text-gray-600" aria-hidden>
              |
            </span>
            <input
              type="search"
              placeholder="Search events…"
              className="w-28 min-w-[6rem] rounded border border-green-500/40 bg-black/60 px-2 py-1 text-[10px] text-gray-100 shadow-inner placeholder:text-gray-500 focus:border-green-400/60 focus:outline-none focus:ring-1 focus:ring-green-500/30"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <p className="mb-2 shrink-0 text-[10px] text-gray-500">
            Showing {displaySteps.length} of {analysisDetail.steps.length} stored events
          </p>

          <h3 className="mb-2 shrink-0 text-xs font-semibold text-gray-400">Event timeline</h3>
          <StepLogList
            steps={displaySteps}
            emptyMessage="No events match this filter."
            fillHeight
          />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded bg-black/30 px-1.5 py-1">
      <div className="truncate text-gray-500">{label}</div>
      <div className="truncate font-medium text-gray-200">{value}</div>
    </div>
  );
}
