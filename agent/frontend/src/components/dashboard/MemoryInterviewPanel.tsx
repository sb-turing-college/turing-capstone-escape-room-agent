import { useEffect, useMemo } from "react";

import { resolveMemorySessionId } from "../../lib/memorySession";
import { memorySourceDisplayLabel } from "../../lib/memorySourceLabels";
import { useAgentStore } from "../../store/agentStore";
import { RunInterviewChat } from "../RunInterviewChat";

export function AgentMemoryPanel() {
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const runs = useAgentStore((s) => s.runs);
  const analysisDetail = useAgentStore((s) => s.analysisDetail);
  const activeMemorySessionId = useAgentStore((s) => s.activeMemorySessionId);
  const memorySnippets = useAgentStore((s) => s.memorySnippets);
  const storedEntries = useAgentStore((s) => s.memoryEntries);
  const refreshMemory = useAgentStore((s) => s.refreshMemory);

  const memorySessionId = useMemo(
    () =>
      resolveMemorySessionId(runs, analysisRunId, {
        detailSessionId:
          analysisDetail?.run_id === analysisRunId
            ? analysisDetail.memory_session_id
            : null,
        activeSessionId: activeMemorySessionId,
      }),
    [runs, analysisRunId, analysisDetail, activeMemorySessionId],
  );

  useEffect(() => {
    if (!memorySessionId) return;
    void refreshMemory(memorySessionId);
  }, [memorySessionId, refreshMemory]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-lg border border-purple-900/40 bg-panel/80 p-4">
      <h2 className="mb-3 shrink-0 text-sm font-semibold text-accent">Agent Memory</h2>
      <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-0.5">
        {!analysisRunId && (
          <li className="text-xs text-gray-500">
            Select a finished run in Sessions to view memory for this playthrough.
          </li>
        )}
        {analysisRunId && !memorySessionId && (
          <li className="text-xs text-gray-500">Loading session memory…</li>
        )}
        {memorySessionId && storedEntries.length === 0 && memorySnippets.length === 0 && (
          <li className="text-xs text-gray-500">No memories for this session yet.</li>
        )}
        {storedEntries.map((entry, index) => (
          <li
            key={entry.id}
            className="rounded border border-purple-900/35 bg-black/25 p-2.5 text-[10px] leading-relaxed"
          >
            <div className="mb-1.5 flex items-baseline justify-between gap-2 border-b border-gray-800/80 pb-1">
              <span className="text-[11px] font-medium text-accent">Memory {index + 1}</span>
              <span className="shrink-0 text-[9px] text-gray-500">
                {memorySourceDisplayLabel(entry.source)}
              </span>
            </div>
            <p className="whitespace-pre-wrap text-gray-200">{entry.document}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AgentChatPanel() {
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const runs = useAgentStore((s) => s.runs);
  const analysisDetail = useAgentStore((s) => s.analysisDetail);

  const selectedRun = runs.find((r) => r.run_id === analysisRunId);
  const canInterview =
    selectedRun != null && selectedRun.status !== "running" && analysisRunId != null;

  const explorerModel =
    analysisDetail?.run_id === analysisRunId
      ? analysisDetail.explorer_model
      : selectedRun?.explorer_model ?? "";

  return (
    <div className="flex h-full max-h-full min-h-0 flex-col rounded-lg border border-purple-900/40 bg-panel/80 p-4">
      <h2 className="mb-3 shrink-0 text-sm font-semibold text-accent">Agent Chat</h2>
      <div className="flex min-h-0 flex-1 flex-col">
        {canInterview && analysisRunId ? (
          <RunInterviewChat runId={analysisRunId} explorerModel={explorerModel} fillHeight />
        ) : (
          <p className="rounded border border-gray-800 bg-black/20 p-4 text-xs text-gray-500">
            Select a run in &ldquo;Sessions&rdquo; to interview the model.
          </p>
        )}
      </div>
    </div>
  );
}
