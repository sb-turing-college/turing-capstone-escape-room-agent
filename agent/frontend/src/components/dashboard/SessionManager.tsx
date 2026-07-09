import {
  continueRunCommandTooltip,
  cumulativeCommandCountForRun,
  formatSegmentCommandBudget,
  isContinueSegmentRun,
  liveSendCommandCount,
  resolveRunMaxSteps,
} from "../../lib/stepLogUtils";
import { formatRunCompletionDate } from "../../lib/memorySession";
import { useAgentStore } from "../../store/agentStore";

type SessionManagerProps = {
  hoveredRunId: string | null;
  onHoverRunId: (runId: string | null) => void;
  onSelectFinishedRun: (runId: string) => void;
};

export function SessionManager({
  hoveredRunId,
  onHoverRunId,
  onSelectFinishedRun,
}: SessionManagerProps) {
  const runs = useAgentStore((s) => s.runs);
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const runId = useAgentStore((s) => s.runId);
  const isRunning = useAgentStore((s) => s.isRunning);
  const liveSteps = useAgentStore((s) => s.liveSteps);
  const liveRunMaxSteps = useAgentStore((s) => s.liveRunMaxSteps);

  const liveCommandCount = liveSendCommandCount(liveSteps);
  const liveRun = isRunning && runId ? runs.find((r) => r.run_id === runId) : null;
  const liveMaxSteps = resolveRunMaxSteps({
    run: liveRun,
    isLiveRun: Boolean(liveRun),
    liveRunMaxSteps,
  });
  const liveTotalCommands =
    liveRun != null
      ? cumulativeCommandCountForRun(liveRun, runs, liveCommandCount)
      : liveCommandCount;
  const commandBudget = formatSegmentCommandBudget(
    liveCommandCount,
    liveMaxSteps,
    liveTotalCommands,
  );

  return (
    <div className="flex flex-col rounded-lg border border-purple-900/40 bg-panel/80 p-2.5 lg:h-full lg:min-h-0">
      <div className="mb-1.5">
        <h2 className="text-sm font-semibold text-accent">Session List</h2>
      </div>

      {isRunning && runId && (
        <div className="mb-2.5 rounded border border-green-500/40 bg-green-950/20 px-3 py-1.5 text-xs">
          <span className="font-semibold text-green-300">● Live run</span>
          <span className="ml-2 font-mono text-gray-300">{runId.slice(0, 8)}…</span>
          {liveRun && (
            <span className="ml-2 text-gray-400">
              {liveRun.explorer_model.split("/").pop()} · {commandBudget} commands
            </span>
          )}
          <p className="mt-1 text-[10px] text-gray-500">Switch to the Live tab to watch.</p>
        </div>
      )}

      <div className="overflow-x-auto lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
        <table className="w-full text-left text-[11px]">
          <thead className="sticky top-0 z-10 bg-panel text-gray-400">
            <tr>
              <th className="pb-1.5 pr-2">Run</th>
              <th className="pb-1.5 pr-2">Completion date</th>
              <th className="max-w-[4.5rem] pb-1.5 pr-2">Model</th>
              <th className="pb-1.5 pr-2">Commands</th>
              <th className="pb-1.5">Status</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run, index) => {
              const selected = analysisRunId === run.run_id;
              const isLive = runId === run.run_id && isRunning;
              const highlighted = hoveredRunId === run.run_id;
              const runNumber = runs.length - index;
              return (
                <tr
                  key={run.run_id}
                  className={`cursor-pointer border-t border-gray-800 ${
                    selected
                      ? highlighted
                        ? "bg-accent/35 text-gray-200 ring-1 ring-inset ring-accent/65"
                        : "bg-accent/20"
                      : highlighted
                        ? "bg-accent/30 text-gray-200 ring-1 ring-inset ring-accent/60"
                        : isLive
                          ? "bg-green-950/20"
                          : "hover:bg-white/5"
                  }`}
                  onMouseEnter={() => onHoverRunId(run.run_id)}
                  onMouseLeave={() => onHoverRunId(null)}
                  onClick={() => onSelectFinishedRun(run.run_id)}
                  title={
                    run.status === "running"
                      ? "Run in progress — use Live tab"
                      : "Select to configure resume or new attempt"
                  }
                >
                  <td
                    className={`py-1.5 pr-2 tabular-nums ${
                      highlighted ? "font-semibold text-gray-100" : "text-gray-400"
                    }`}
                  >
                    {runNumber}
                  </td>
                  <td className="whitespace-nowrap py-1.5 pr-2">
                    {formatRunCompletionDate(run)}
                  </td>
                  <td
                    className="max-w-[4.5rem] truncate py-1.5 pr-2"
                    title={run.explorer_model}
                  >
                    {run.explorer_model.split("/").pop()}
                  </td>
                  <td className="py-1.5 pr-2">
                    <span
                      className="inline-flex items-center gap-0.5"
                      title={
                        isLive
                          ? undefined
                          : continueRunCommandTooltip(run, runs)
                      }
                    >
                      <span>
                        {isLive
                          ? cumulativeCommandCountForRun(run, runs, liveCommandCount)
                          : cumulativeCommandCountForRun(run, runs)}
                      </span>
                      {isContinueSegmentRun(run) && (
                        <span
                          className="text-[10px] leading-none text-gray-500"
                          aria-hidden
                        >
                          ↪
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="py-1.5">{run.status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-[10px] text-gray-500">
        Click a finished run to configure resume or new attempt above. Switch to Review for
        memory, chat, and event timeline.
      </p>
    </div>
  );
}
