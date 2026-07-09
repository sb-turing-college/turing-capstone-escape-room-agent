import { useEffect, useMemo, useState } from "react";

import {
  continueRun,
  fetchRunDetail,
  retryRun,
  startRun,
} from "../../hooks/useAgentSocket";
import { memorySessionIdForRun } from "../../lib/memorySession";
import {
  actionButtonClass,
} from "../../lib/actionButtonStyles";
import { stepNumberOnWheel, useWheelControl } from "../../lib/wheelInput";
import { useAgentStore } from "../../store/agentStore";
import { SessionLearningCurve, type ChartPoint } from "./SessionLearningCurve";

type RunControlPanelProps = {
  onRunStarted: () => void;
  chartPoints: ChartPoint[];
  hoveredRunId: string | null;
  onHoverRunId: (runId: string | null) => void;
  onSelectRun: (runId: string) => void;
};

const inputClass =
  "min-w-0 rounded border border-gray-700 bg-zinc-900 px-2 py-1.5 text-gray-100";
const selectClass =
  "rounded border border-gray-700 bg-zinc-900 px-2 py-1.5 text-xs text-gray-100";
const numericInputClass = `${inputClass} w-[2.75rem] px-1 text-center tabular-nums [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none`;
const metaDivider = (
  <span className="text-gray-600 select-none" aria-hidden>
    |
  </span>
);

export function RunControlPanel({
  onRunStarted,
  chartPoints,
  hoveredRunId,
  onHoverRunId,
  onSelectRun,
}: RunControlPanelProps) {
  const isRunning = useAgentStore((s) => s.isRunning);
  const pendingNewSession = useAgentStore((s) => s.pendingNewSession);
  const analysisRunId = useAgentStore((s) => s.analysisRunId);
  const runs = useAgentStore((s) => s.runs);
  const models = useAgentStore((s) => s.models);
  const maxSteps = useAgentStore((s) => s.maxSteps);
  const maxHumanAssists = useAgentStore((s) => s.maxHumanAssists);
  const setMaxSteps = useAgentStore((s) => s.setMaxSteps);
  const setMaxHumanAssists = useAgentStore((s) => s.setMaxHumanAssists);
  const setSelectedModel = useAgentStore((s) => s.setSelectedModel);
  const selectedModel = useAgentStore((s) => s.selectedModel);
  const setPendingNewSession = useAgentStore((s) => s.setPendingNewSession);

  const draftMode = pendingNewSession != null && analysisRunId == null;
  const fromList = analysisRunId ? runs.find((r) => r.run_id === analysisRunId) : null;
  const showResume = fromList != null && fromList.success !== true;
  const showNewAttempt = fromList != null;

  const selectedRunLabel = useMemo(() => {
    if (draftMode || !fromList) return null;
    const runIndex = runs.findIndex((r) => r.run_id === fromList.run_id);
    const label = runIndex >= 0 ? runs.length - runIndex : fromList.run_id.slice(0, 8);
    return `Run ${label}`;
  }, [draftMode, fromList, runs]);

  const [hint, setHint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (draftMode || !analysisRunId) return;
    const run = runs.find((r) => r.run_id === analysisRunId);
    if (run) setMaxHumanAssists(run.max_human_assists ?? 0);
    setHint("");
    setError(null);
  }, [draftMode, analysisRunId, runs, setMaxHumanAssists]);

  const maxStepsRef = useWheelControl<HTMLLabelElement>(
    (event) => {
      const next = stepNumberOnWheel(event.deltaY, maxSteps, 5, 200);
      if (next !== maxSteps) setMaxSteps(next);
    },
    !submitting,
  );

  const humanAssistsRef = useWheelControl<HTMLLabelElement>(
    (event) => {
      const next = stepNumberOnWheel(event.deltaY, maxHumanAssists, 0, 3);
      if (next !== maxHumanAssists) setMaxHumanAssists(next);
    },
    !submitting,
  );

  const handleCreateSession = () => {
    if (!selectedModel) return;
    setPendingNewSession(selectedModel);
  };

  const createSessionButton = (
    <button
      type="button"
      className={actionButtonClass}
      disabled={!selectedModel || submitting}
      onClick={handleCreateSession}
    >
      Create Session
    </button>
  );

  const commandCounter = (
    <SessionLearningCurve
      variant="embedded"
      chartPoints={chartPoints}
      runs={runs}
      hoveredRunId={hoveredRunId}
      onHoverRunId={onHoverRunId}
      onSelectRun={onSelectRun}
    />
  );

  if (isRunning) {
    return (
      <div className="rounded-lg border border-purple-900/40 bg-panel/80 px-3 py-2">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[45fr_55fr] lg:gap-4">
          <div>
            <h2 className="text-sm font-semibold text-accent">Run Control</h2>
            <p className="mt-2 text-xs text-gray-500">
              A session is running. View progress on the Live tab or start another session.
            </p>
            <div className="mt-3">{createSessionButton}</div>
          </div>
          <div className="min-h-[7rem] lg:border-l lg:border-purple-900/30 lg:pl-4">
            {commandCounter}
          </div>
        </div>
      </div>
    );
  }

  if (!draftMode && (!analysisRunId || !fromList || fromList.status === "running")) {
    return (
      <div className="rounded-lg border border-purple-900/40 bg-panel/80 px-3 py-2">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[45fr_55fr] lg:gap-4">
          <div>
            <h2 className="text-sm font-semibold text-accent">Run Control</h2>
            <p className="mt-2 text-xs text-gray-500">
              Select a run below or click &ldquo;Create Session&rdquo;.
            </p>
            <div className="mt-3">{createSessionButton}</div>
          </div>
          <div className="min-h-[7rem] lg:border-l lg:border-purple-900/30 lg:pl-4">
            {commandCounter}
          </div>
        </div>
      </div>
    );
  }

  const handleDraftModelChange = (model: string) => {
    setSelectedModel(model);
    useAgentStore.getState().setPendingNewSession(model);
  };

  const handleStartNewSession = async () => {
    const model = pendingNewSession?.model;
    if (!model) return;

    setSubmitting(true);
    setError(null);
    const hintText = hint.trim() || null;
    try {
      const store = useAgentStore.getState();
      store.clearAnalysis();
      store.resetLiveState();
      store.setIsRunning(true);
      const { run_id } = await startRun(model, maxSteps, null, maxHumanAssists, hintText);
      store.clearPendingNewSession();
      store.setRunId(run_id);
      store.setActiveMemorySessionId(run_id);
      store.clearMemorySnippets();
      void store.refreshMemory(run_id);
      store.setStatusMessage("Session Running");
      setHint("");
      onRunStarted();
    } catch (err) {
      useAgentStore.getState().setIsRunning(false);
      setError(err instanceof Error ? err.message : "Start failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleExistingRun = async (mode: "resume" | "retry") => {
    if (!analysisRunId || !fromList) return;

    setSubmitting(true);
    setError(null);
    const hintText = hint.trim() || null;
    try {
      const { run_id } =
        mode === "resume"
          ? await continueRun(analysisRunId, {
              hint: hintText,
              maxSteps,
              maxHumanAssists,
            })
          : await retryRun(analysisRunId, {
              hint: hintText,
              maxSteps,
              maxHumanAssists,
            });

      const store = useAgentStore.getState();
      store.clearAnalysis();
      store.resetLiveState();
      store.setIsRunning(true);
      store.setRunId(run_id);
      store.setLastRunResult(null);
      store.setStatusMessage("Session Running");
      const sessionId = memorySessionIdForRun(fromList, runs);
      store.setActiveMemorySessionId(sessionId);
      store.clearMemorySnippets();
      void store.refreshMemory(sessionId);
      setHint("");
      if (mode === "resume") {
        void fetchRunDetail(analysisRunId);
      }
      onRunStarted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run");
    } finally {
      setSubmitting(false);
    }
  };

  const displayModel = draftMode
    ? pendingNewSession?.model ?? ""
    : fromList?.explorer_model ?? "";

  return (
    <div className="rounded-lg border border-purple-900/40 bg-panel/80 px-3 py-2">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[45fr_55fr] lg:gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-accent">Run Control</h2>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs">
            {draftMode ? (
              <span className="text-gray-400">Draft</span>
            ) : (
              selectedRunLabel && (
                <span className="font-medium text-gray-300">{selectedRunLabel}</span>
              )
            )}

            {(draftMode || displayModel) && (
              <>
                {metaDivider}
                {draftMode ? (
                  <select
                    className={`${selectClass} max-w-[14rem]`}
                    value={displayModel}
                    onChange={(e) => handleDraftModelChange(e.target.value)}
                    disabled={submitting}
                    aria-label="Explorer model"
                  >
                    {models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                ) : (
                  displayModel && (
                    <span className="truncate text-gray-400" title={displayModel}>
                      {displayModel.split("/").pop()}
                    </span>
                  )
                )}
              </>
            )}

            {metaDivider}

            <label ref={maxStepsRef} className="flex items-center gap-2">
              <span className="shrink-0 text-gray-400">Max commands</span>
              <input
                type="number"
                min={5}
                max={200}
                className={numericInputClass}
                value={maxSteps}
                onChange={(e) => setMaxSteps(Number(e.target.value))}
                disabled={submitting}
              />
            </label>
            <label
              ref={humanAssistsRef}
              className="flex items-center gap-2"
              title="How often the agent may ask you a question (Give Hint always available)."
            >
              <span className="shrink-0 text-gray-400">Human assists</span>
              <input
                type="number"
                min={0}
                max={3}
                className={numericInputClass}
                value={maxHumanAssists}
                onChange={(e) => setMaxHumanAssists(Number(e.target.value))}
                disabled={submitting}
              />
            </label>
          </div>

          <textarea
            className="w-full rounded border border-gray-700 bg-black/40 px-2 py-1.5 text-xs text-gray-100"
            rows={2}
            placeholder="Optional hint for the agent…"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            disabled={submitting}
          />

          <div className="flex flex-wrap gap-2">
            {createSessionButton}
            {draftMode ? (
              <button
                type="button"
                title="Start a fresh game with a clean memory session"
                className={actionButtonClass}
                onClick={() => void handleStartNewSession()}
                disabled={submitting || !pendingNewSession?.model}
              >
                ▶ Start Run
              </button>
            ) : (
              <>
                {showResume && (
                  <button
                    type="button"
                    title="Pick up where this run stopped"
                    className={actionButtonClass}
                    onClick={() => void handleExistingRun("resume")}
                    disabled={submitting}
                  >
                    ▶ Resume Run
                  </button>
                )}
                {showNewAttempt && (
                  <button
                    type="button"
                    title="Fresh game, keep memory and chat"
                    className={actionButtonClass}
                    onClick={() => void handleExistingRun("retry")}
                    disabled={submitting}
                  >
                    ↻ New Attempt
                  </button>
                )}
              </>
            )}
          </div>

          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>

        <div className="min-h-[7rem] lg:border-l lg:border-purple-900/30 lg:pl-4">
          {commandCounter}
        </div>
      </div>
    </div>
  );
}
