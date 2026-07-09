import type { RunSummary } from "../types/agent";
import { cumulativeCommandCountForRun } from "./stepLogUtils";

type RunSessionFields = Pick<
  RunSummary,
  "run_id" | "memory_session_id" | "continued_from_run_id"
>;

/** Walk the continue chain to the root run (for legacy rows missing memory_session_id). */
export function rootRunForChain(
  run: RunSessionFields,
  runs: RunSessionFields[],
): RunSessionFields {
  let current = run;
  const seen = new Set<string>([current.run_id]);
  while (current.continued_from_run_id) {
    const parent = runs.find((r) => r.run_id === current.continued_from_run_id);
    if (!parent || seen.has(parent.run_id)) break;
    seen.add(parent.run_id);
    current = parent;
  }
  return current;
}

/** Root episodic memory scope for a run (Option B: root run id of the chain). */
export function memorySessionIdForRun(run: RunSessionFields, runs?: RunSessionFields[]): string {
  if (run.memory_session_id) return run.memory_session_id;
  if (runs && runs.length > 0) {
    return rootRunForChain(run, runs).run_id;
  }
  return run.run_id;
}

/** All runs belonging to the same memory session (default: newest first). */
export function runsInMemorySession(
  runs: RunSummary[],
  sessionId: string,
  order: "newest" | "oldest" = "newest",
): RunSummary[] {
  const filtered = runs.filter((run) => memorySessionIdForRun(run, runs) === sessionId);
  filtered.sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  );
  return order === "oldest" ? filtered.reverse() : filtered;
}

function runOutcomeLabel(run: Pick<RunSummary, "success" | "status">): string {
  if (run.success === true) return "completed";
  if (run.success === false) return "failed";
  return run.status;
}

function formatRunDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatRunCompletionDate(
  run: Pick<RunSummary, "finished_at" | "status">,
): string {
  if (run.finished_at) return formatRunDateTime(run.finished_at);
  if (run.status === "running") return "in progress";
  return "—";
}

/** Short label for session pickers (date + model). */
export function formatMemorySessionOptionLabel(sessionRuns: RunSummary[]): string {
  if (sessionRuns.length === 0) return "Unknown session";

  const latest = sessionRuns[0];
  const model = latest.explorer_model.split("/").pop() ?? latest.explorer_model;
  return `${formatRunCompletionDate(latest)} · ${model}`;
}

/** Human-readable label for a memory session (newest run first in `sessionRuns`). */
export function formatMemorySessionLabel(sessionRuns: RunSummary[]): string {
  if (sessionRuns.length === 0) return "Unknown session";

  const latest = sessionRuns[0];
  const model = latest.explorer_model.split("/").pop() ?? latest.explorer_model;
  const count = sessionRuns.length;
  const attempts = `${count} ${count === 1 ? "attempt" : "attempts"}`;
  const outcome = runOutcomeLabel(latest);
  const outcomePart = count === 1 ? outcome : `latest ${outcome}`;
  const commands = cumulativeCommandCountForRun(latest, sessionRuns);
  const completed = formatRunCompletionDate(latest);

  return `${completed} · ${model} · ${attempts} · ${outcomePart} · ${commands} commands`;
}

/** Resolve session id for review/live UI without falling back to a child run_id. */
export function resolveMemorySessionId(
  runs: RunSummary[],
  runId: string | null | undefined,
  options: {
    detailSessionId?: string | null;
    activeSessionId?: string | null;
  } = {},
): string | null {
  if (!runId) return options.activeSessionId ?? null;
  const run = runs.find((r) => r.run_id === runId);
  if (run) return memorySessionIdForRun(run, runs);
  if (options.detailSessionId) return options.detailSessionId;
  if (options.activeSessionId) return options.activeSessionId;
  return null;
}
