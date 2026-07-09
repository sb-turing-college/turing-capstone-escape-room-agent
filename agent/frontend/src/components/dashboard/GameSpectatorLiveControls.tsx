import { useState } from "react";

import { pauseRun, resumeRun, stopRun } from "../../hooks/useAgentSocket";
import { actionButtonClass } from "../../lib/actionButtonStyles";
import { fetchRuns } from "../../api/agentApi";
import { useAgentStore } from "../../store/agentStore";

export function SpectatorLiveButtons() {
  const { isRunning, isPaused, runId, setStatusMessage } = useAgentStore();
  const [pausing, setPausing] = useState(false);

  if (!isRunning || !runId) return null;

  const handleStop = async () => {
    const store = useAgentStore.getState();
    store.setIsRunning(false);
    store.setIsPaused(false);
    store.setPauseContext({ initiator: null });
    store.setStatusMessage("Stopping…");
    try {
      await stopRun(runId);
    } catch (err) {
      store.setStatusMessage(err instanceof Error ? err.message : "Failed to stop run");
    }
    void fetchRuns();
  };

  const handleGiveHint = async () => {
    setPausing(true);
    try {
      await pauseRun(runId);
      setStatusMessage("Pausing before the next game action…");
    } catch (err) {
      setStatusMessage(err instanceof Error ? err.message : "Failed to pause run");
    } finally {
      setPausing(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        className="inline-flex items-center gap-1.5 rounded border border-red-400/80 px-3 py-1.5 text-xs text-red-300 disabled:opacity-40"
        onClick={() => void handleStop()}
      >
        <span aria-hidden="true">⏹</span>
        Stop
      </button>
      <button
        type="button"
        className="inline-flex items-center gap-1.5 rounded border border-orange-400/80 px-3 py-1.5 text-xs text-orange-200 disabled:opacity-40"
        onClick={() => void handleGiveHint()}
        disabled={isPaused || pausing}
        title="Pauses before its next game action"
      >
        <span aria-hidden="true">⏸</span>
        {pausing ? "Pausing…" : "Give Hint"}
      </button>
    </div>
  );
}

export function SpectatorPausePanel() {
  const { isRunning, isPaused, pauseInitiator, runId, setStatusMessage } = useAgentStore();
  const [hintText, setHintText] = useState("");
  const [resuming, setResuming] = useState(false);

  if (!isRunning || !isPaused || !runId || pauseInitiator === "agent") return null;

  const handleResume = async (humanResponse: string | null) => {
    setResuming(true);
    try {
      await resumeRun(runId, humanResponse);
      setHintText("");
    } catch (err) {
      setStatusMessage(err instanceof Error ? err.message : "Failed to resume run");
    } finally {
      setResuming(false);
    }
  };

  return (
    <div className="mb-2 rounded border border-orange-500/50 bg-orange-950/25 p-2">
      <p className="mb-1.5 text-[10px] font-semibold text-orange-200">Paused — optional hint</p>
      <textarea
        className="mb-1.5 w-full rounded border border-gray-700 bg-black/40 px-2 py-1 text-[10px] text-gray-100"
        rows={2}
        placeholder="Hint for the agent…"
        value={hintText}
        onChange={(e) => setHintText(e.target.value)}
        disabled={resuming}
      />
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          className="rounded bg-orange-500 px-2 py-0.5 text-[10px] font-semibold text-black disabled:opacity-40"
          onClick={() => void handleResume(hintText.trim() || null)}
          disabled={resuming || !hintText.trim()}
        >
          Send &amp; Resume
        </button>
        <button
          type="button"
          className="rounded border border-orange-400/80 px-2 py-0.5 text-[10px] text-orange-200 disabled:opacity-40"
          onClick={() => void handleResume(null)}
          disabled={resuming}
        >
          Resume
        </button>
      </div>
    </div>
  );
}

export function AgentQuestionModal() {
  const {
    isRunning,
    isPaused,
    pauseInitiator,
    agentTheory,
    agentQuestion,
    runId,
    setStatusMessage,
  } = useAgentStore();
  const [answerText, setAnswerText] = useState("");
  const [resuming, setResuming] = useState(false);

  if (!isRunning || !isPaused || !runId || pauseInitiator !== "agent") return null;

  const handleResume = async (humanResponse: string | null) => {
    setResuming(true);
    try {
      await resumeRun(runId, humanResponse);
      setAnswerText("");
    } catch (err) {
      setStatusMessage(err instanceof Error ? err.message : "Failed to resume run");
    } finally {
      setResuming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!resuming) void handleResume(answerText.trim() || null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-purple-500/60 bg-zinc-950 p-4 shadow-xl">
        <p className="mb-2 text-xs font-semibold text-purple-200">Agent question</p>
        {agentTheory ? (
          <div className="mb-2 rounded border border-gray-700 bg-black/40 p-2">
            <p className="mb-1 text-[10px] font-medium text-gray-400">Agent status</p>
            <p className="text-[11px] leading-relaxed text-gray-100">{agentTheory}</p>
          </div>
        ) : null}
        {agentQuestion ? (
          <div className="mb-3 rounded border border-purple-800/60 bg-purple-950/30 p-2">
            <p className="mb-1 text-[10px] font-medium text-purple-300">Question</p>
            <p className="text-[11px] leading-relaxed text-gray-100">{agentQuestion}</p>
          </div>
        ) : null}
        <textarea
          className="mb-3 w-full rounded border border-gray-700 bg-black/40 px-2 py-1.5 text-[11px] text-gray-100"
          rows={3}
          placeholder="Your answer (optional)…"
          value={answerText}
          onChange={(e) => setAnswerText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={resuming}
        />
        <div className="flex justify-end">
          <button
            type="button"
            className={actionButtonClass}
            onClick={() => void handleResume(answerText.trim() || null)}
            disabled={resuming}
          >
            {answerText.trim() ? "Send & Resume" : "Resume without answer"}
          </button>
        </div>
      </div>
    </div>
  );
}
