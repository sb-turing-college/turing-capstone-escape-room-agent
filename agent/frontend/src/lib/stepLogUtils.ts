import type { AgentEvent, GameState, LiveStep, ReasoningItem, RunSummary, StoredStep } from "../types/agent";
import { normalizeMemorySource, type MemorySourceKind } from "./memorySourceLabels";

export { mapGraphFromSteps } from "./mapGraph";

const REASONING_TYPES = new Set([
  "thought",
  "action",
  "observation",
  "memory_retrieved",
  "memory_stored",
  "thinking",
  "blocked",
]);

export type StepFilter =
  | "all"
  | "gameplay"
  | "commands"
  | "thoughts"
  | "map"
  | "memory"
  | "system"
  | "blocked";

export function summarizeObservation(raw: string): string {
  try {
    const data = JSON.parse(raw) as Record<string, unknown>;
    const room = String(data.room ?? "?");
    const inv = Array.isArray(data.inventory)
      ? (data.inventory as string[]).join(", ") || "empty"
      : "?";
    const visible = Array.isArray(data.visible_items)
      ? (data.visible_items as string[]).join(", ") || "none"
      : "?";
    const ending = data.ending != null ? ` | ending=${String(data.ending)}` : "";
    return `room=${room} | visible: ${visible} | inv: ${inv}${ending}`;
  } catch {
    return raw.slice(0, 180);
  }
}

/**
 * Legacy synthetic thoughts (pre-fallback removal) started every line with "→ ".
 * We treat them as empty so replay runs don't show stale placeholder text.
 */
export function isSyntheticThought(content: string): boolean {
  const lines = content.split("\n").map((line) => line.trim()).filter(Boolean);
  return lines.length > 0 && lines.every((line) => line.startsWith("→"));
}

export function thoughtDisplayContent(content: string | undefined | null): string {
  const raw = content ?? "";
  return isSyntheticThought(raw) ? "" : raw;
}

export function hasThoughtContent(content: string | undefined | null): boolean {
  return thoughtDisplayContent(content).trim().length > 0;
}

export function isSendCommandAction(content: string | undefined | null): boolean {
  return (content ?? "").trimStart().toLowerCase().startsWith("send_command:");
}

export function isAskHumanAction(content: string | undefined | null): boolean {
  return (content ?? "").trimStart().toLowerCase().startsWith("ask_human:");
}

export function liveStepFromEvent(event: AgentEvent): LiveStep | null {
  const id = `${event.type}-${event.step ?? 0}-${event.content?.slice(0, 24) ?? ""}-${Math.random()}`;
  const base = { id, step: event.step, room: event.room };

  if (event.type === "action" && event.content) {
    if (isSendCommandAction(event.content)) {
      const command = event.content.replace(/^send_command:\s*/i, "").trim();
      return { ...base, kind: "command", content: command || event.content };
    }
    if (isAskHumanAction(event.content)) {
      const question = event.content.replace(/^ask_human:\s*/i, "").trim();
      return { ...base, kind: "assist", content: question || event.content };
    }
    return { ...base, kind: "action", content: event.content };
  }
  if (event.type === "game_update" && event.content) {
    return { ...base, kind: "response", content: event.content };
  }
  if (event.type === "observation" && event.content) {
    return { ...base, kind: "detail", content: summarizeObservation(event.content) };
  }
  if (event.type === "thinking" && event.content) {
    return { ...base, kind: "thinking", content: event.content };
  }
  if (event.type === "thought") {
    const raw = event.content ?? "";
    const synthetic = isSyntheticThought(raw);
    const content = synthetic ? "" : raw;
    return {
      ...base,
      kind: "thought",
      content,
      synthetic: synthetic || undefined,
    };
  }
  if (event.type === "system" && event.content) {
    return { ...base, kind: "system", content: event.content };
  }
  if (event.type === "human_hint" && event.content) {
    return { ...base, kind: "assist", content: `Hint: ${event.content}` };
  }
  if (event.type === "human_response" && event.content) {
    return { ...base, kind: "assist", content: `Answer: ${event.content}` };
  }
  if (event.type === "blocked" && event.content) {
    return { ...base, kind: "blocked", content: event.content };
  }
  if (event.type === "room_visited") {
    const label = event.label ?? event.room ?? event.content ?? "unknown room";
    const from = event.from ? ` (from ${event.from})` : "";
    return { ...base, kind: "map", content: `Entered ${label}${from}` };
  }
  if (event.type === "item_discovered") {
    const item = event.item ?? event.content ?? "item";
    return { ...base, kind: "map", content: `Discovered: ${item}` };
  }
  if (
    (event.type === "memory_retrieved" || event.type === "memory_stored") &&
    event.content
  ) {
    return { ...base, kind: "memory", content: event.content };
  }
  if (event.type === "run_started") {
    const budget =
      typeof event.max_steps === "number" ? ` · max ${event.max_steps} commands` : "";
    return {
      ...base,
      kind: "system",
      content: `Run started (${event.explorer_model ?? "model"})${budget}`,
    };
  }
  if (event.type === "run_complete") {
    const cmd = event.commands ?? event.steps ?? "?";
    const ev = event.steps ?? "?";
    return {
      ...base,
      kind: "system",
      content: event.success
        ? `Run complete — ${cmd} commands, ${ev} events logged`
        : "Run finished without reaching the ending",
    };
  }
  if (event.type === "run_failed") {
    return { ...base, kind: "system", content: `Run failed: ${event.reason ?? "unknown"}` };
  }
  return null;
}

export function storedStepToEvent(step: StoredStep): AgentEvent {
  return {
    type: step.type as AgentEvent["type"],
    content: step.content,
    step: step.step_number,
    room: step.room,
    ...(step.extra ?? {}),
  };
}

export function liveStepFromStored(step: StoredStep): LiveStep | null {
  return liveStepFromEvent(storedStepToEvent(step));
}

export function commandCountFromSteps(steps: StoredStep[]): number {
  return steps.filter((s) => s.type === "action" && isSendCommandAction(s.content)).length;
}

/** Live send_command count — excludes ask_human and other non-game actions. */
export function liveSendCommandCount(steps: LiveStep[]): number {
  return steps.filter((s) => s.kind === "command").length;
}

export function segmentCommandCountForRun(
  run: Pick<RunSummary, "commands_count" | "steps_count">,
  steps?: StoredStep[],
): number {
  return commandCountForRun(run, steps);
}

/** @deprecated Use segmentCommandCountForRun or cumulativeCommandCountForRun explicitly. */
export function commandCountForRun(
  run: Pick<RunSummary, "commands_count" | "steps_count">,
  steps?: StoredStep[],
): number {
  if (typeof run.commands_count === "number") return run.commands_count;
  if (steps) return commandCountFromSteps(steps);
  return 0;
}

export function isContinueSegmentRun(
  run: Pick<RunSummary, "continued_from_run_id" | "is_fresh_attempt">,
): boolean {
  return Boolean(run.continued_from_run_id && !run.is_fresh_attempt);
}

export function cumulativeCommandCountForRun(
  run: Pick<
    RunSummary,
    | "run_id"
    | "commands_count"
    | "cumulative_commands_count"
    | "continued_from_run_id"
    | "is_fresh_attempt"
    | "steps_count"
  >,
  runs?: RunSummary[],
  liveSegmentOverride?: number,
): number {
  const segment =
    liveSegmentOverride ?? segmentCommandCountForRun(run);
  if (liveSegmentOverride === undefined && typeof run.cumulative_commands_count === "number") {
    return run.cumulative_commands_count;
  }
  if (!isContinueSegmentRun(run) || !runs?.length) {
    return segment;
  }
  const parent = runs.find((entry) => entry.run_id === run.continued_from_run_id);
  if (!parent) return segment;
  return cumulativeCommandCountForRun(parent, runs) + segment;
}

export function continueRunCommandTooltip(
  run: Pick<
    RunSummary,
    | "continued_from_run_id"
    | "is_fresh_attempt"
    | "commands_count"
    | "cumulative_commands_count"
    | "run_id"
    | "steps_count"
  >,
  runs: RunSummary[],
): string | undefined {
  if (!isContinueSegmentRun(run)) return undefined;
  const total = cumulativeCommandCountForRun(run, runs);
  const segment = segmentCommandCountForRun(run);
  const previous = Math.max(0, total - segment);
  return `${total} total commands (${segment} in this segment, ${previous} in previous runs)`;
}

export function formatSegmentCommandBudget(
  segmentCount: number,
  maxSteps: number | null | undefined,
  totalCount?: number,
): string {
  const segmentPart =
    maxSteps != null ? `${segmentCount}/${maxSteps}` : String(segmentCount);
  if (totalCount != null && totalCount > segmentCount) {
    return `${segmentPart} · total ${totalCount}`;
  }
  return segmentPart;
}

/** @deprecated Prefer formatSegmentCommandBudget — kept as alias for live session banner. */
export function formatLiveCommandBudget(
  segmentCount: number,
  maxSteps: number | null | undefined,
  totalCount: number,
): string {
  return formatSegmentCommandBudget(segmentCount, maxSteps, totalCount);
}

/** Segment budget denominator: live WebSocket during active run, else persisted run record. */
export function resolveRunMaxSteps(options: {
  run?: Pick<RunSummary, "max_steps"> | null;
  isLiveRun: boolean;
  liveRunMaxSteps: number | null;
}): number | null {
  if (options.isLiveRun && options.liveRunMaxSteps != null) {
    return options.liveRunMaxSteps;
  }
  if (typeof options.run?.max_steps === "number") {
    return options.run.max_steps;
  }
  return null;
}

export function filterStoredSteps(steps: StoredStep[], filter: StepFilter): StoredStep[] {
  if (filter === "all") return steps;
  return steps.filter((s) => {
    switch (filter) {
      case "gameplay":
        return ["action", "game_update", "observation"].includes(s.type);
      case "commands":
        return s.type === "action" && isSendCommandAction(s.content);
      case "thoughts":
        return s.type === "thought" || s.type === "thinking";
      case "map":
        return s.type === "room_visited" || s.type === "item_discovered";
      case "memory":
        return s.type === "memory_retrieved" || s.type === "memory_stored";
      case "system":
        return (
          s.type === "thinking" ||
          s.type === "system" ||
          s.type === "human_hint" ||
          s.type === "human_response"
        );
      case "blocked":
        return s.type === "blocked";
      default:
        return true;
    }
  });
}

export function stepTypeCounts(steps: StoredStep[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const s of steps) {
    counts[s.type] = (counts[s.type] ?? 0) + 1;
  }
  return counts;
}

export function formatRunDuration(started: string, finished: string | null): string {
  if (!finished) return "—";
  const ms = new Date(finished).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

/** Plain scrollable timeline for the Decision Graph — no xyflow canvas/pan/zoom. */
function inferMemorySource(step: StoredStep): MemorySourceKind | undefined {
  const fromExtra = step.extra?.memory_source;
  if (typeof fromExtra === "string") {
    return normalizeMemorySource(fromExtra);
  }
  if (step.type !== "memory_retrieved" && step.type !== "memory_stored") {
    return undefined;
  }
  if (step.content.includes("(Interview note:")) {
    return normalizeMemorySource("interview");
  }
  return normalizeMemorySource("run_summary");
}

export function reasoningItemsFromSteps(steps: StoredStep[]): ReasoningItem[] {
  return steps
    .filter((s) => REASONING_TYPES.has(s.type))
    .map((step) => ({
      id: `a-${step.step_number}`,
      type: step.type,
      content: step.type === "thought" ? thoughtDisplayContent(step.content) : step.content,
      room: step.room,
      memorySource: inferMemorySource(step),
    }));
}

export function gameStateFromSteps(steps: StoredStep[]): GameState | null {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    const step = steps[i];
    if (step.type !== "game_update" || !step.room) continue;
    const extra = step.extra ?? {};
    return {
      room: step.room,
      text: step.content,
      visible_items: Array.isArray(extra.visible_items)
        ? (extra.visible_items as string[])
        : [],
      inventory: Array.isArray(extra.inventory) ? (extra.inventory as string[]) : [],
      exits:
        extra.exits && typeof extra.exits === "object"
          ? (extra.exits as Record<string, string>)
          : {},
      is_solved: Boolean(extra.is_solved),
      ending: (extra.ending as string | null | undefined) ?? null,
    };
  }
  return null;
}

export function liveStepsFromStored(steps: StoredStep[]): LiveStep[] {
  return steps
    .map((s) => liveStepFromStored(s))
    .filter((s): s is LiveStep => s != null);
}
