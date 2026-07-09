import type { MemorySourceKind } from "../lib/memorySourceLabels";

export type AgentEventType =
  | "thought"
  | "action"
  | "observation"
  | "thinking"
  | "blocked"
  | "system"
  | "memory_retrieved"
  | "memory_stored"
  | "human_hint"
  | "human_response"
  | "room_visited"
  | "item_discovered"
  | "game_update"
  | "run_started"
  | "run_complete"
  | "run_failed"
  | "run_paused"
  | "run_resumed"
  | "ping";

export interface AgentEvent {
  type: AgentEventType;
  content?: string;
  step?: number;
  room?: string | null;
  run_id?: string;
  success?: boolean;
  steps?: number;
  /** Game commands (send_command) used — matches the run budget. */
  commands?: number;
  /** send_command budget for this run (run_started). */
  max_steps?: number;
  reason?: string;
  final_answer?: string;
  visible_items?: string[];
  inventory?: string[];
  exits?: Record<string, string>;
  is_solved?: boolean;
  ending?: string | null;
  label?: string;
  from?: string | null;
  via?: string;
  item?: string;
  explorer_model?: string;
  hint?: string | null;
  human_response?: string | null;
  responded?: boolean;
  initiator?: "human" | "agent";
  agent_theory?: string | null;
  agent_question?: string | null;
  human_assists_used?: number;
  max_human_assists?: number;
  continued_from_run_id?: string | null;
  /** True when this run was started via New Attempt (fresh game). */
  is_fresh_attempt?: boolean;
  memory_session_id?: string | null;
  memory_source?: MemorySourceKind;
}

export interface GameState {
  room: string;
  text: string;
  visible_items: string[];
  inventory: string[];
  exits: Record<string, string>;
  is_solved: boolean;
  ending?: string | null;
}

export interface RunSummary {
  run_id: string;
  session_id: string | null;
  started_at: string;
  finished_at: string | null;
  success: boolean | null;
  steps_count: number;
  /** send_command count for this run segment only. */
  commands_count?: number | null;
  /** send_command count across the full continue lineage (root → this run). */
  cumulative_commands_count?: number | null;
  explorer_model: string;
  memory_model: string;
  status: string;
  error_message?: string | null;
  continued_from_run_id?: string | null;
  /** True when this run was started via New Attempt (fresh game). */
  is_fresh_attempt?: boolean;
  memory_session_id?: string | null;
  max_human_assists?: number;
  human_assists_used?: number;
  /** send_command budget frozen at run start (null on legacy runs). */
  max_steps?: number | null;
}

export interface StoredStep {
  step_number: number;
  type: string;
  content: string;
  room: string | null;
  timestamp: string;
  /** Structured extras (room_visited's from/label, game_update's inventory/exits, ...). */
  extra?: Record<string, unknown> | null;
}

export interface RunDetail extends RunSummary {
  steps: StoredStep[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  memory_saved?: boolean;
}

export interface MemoryEntry {
  id: string;
  document: string;
  source?: string | null;
  run_id?: string | null;
  memory_session_id?: string | null;
}

export interface LiveStep {
  id: string;
  step?: number;
  kind:
    | "command"
    | "action"
    | "assist"
    | "response"
    | "thought"
    | "memory"
    | "system"
    | "map"
    | "detail"
    | "thinking"
    | "blocked";
  content: string;
  room?: string | null;
  /** Legacy flag: stored runs may still contain old "→ send_command" placeholders. */
  synthetic?: boolean;
}

export interface RunResultInfo {
  runId: string;
  success: boolean | null;
  steps: number;
  finalAnswer: string;
  reason?: string;
  explorerModel?: string;
}

import gameConstants from "../shared/game_constants.json";

export const ROOM_LABELS: Record<string, string> = gameConstants.room_labels;

export const NODE_COLORS: Record<string, string> = {
  thought: "#fbbf24",
  action: "#60a5fa",
  observation: "#34d399",
  memory_retrieved: "#c084fc",
  memory_stored: "#c084fc",
  thinking: "#fb923c",
  blocked: "#f87171",
};

/** Event types that only appear in the stored log timeline (not the live Decision Graph). */
export const LOG_ONLY_COLORS = {
  game_update: "#2dd4bf",
  map: "#22d3ee",
  assist: "#f472b6",
  system: "#94a3b8",
} as const;

/** Left-border colors for StepLogList — shared kinds match NODE_COLORS (live view). */
export const STEP_KIND_COLORS: Record<LiveStep["kind"], string> = {
  command: NODE_COLORS.action,
  action: NODE_COLORS.action,
  thought: NODE_COLORS.thought,
  detail: NODE_COLORS.observation,
  thinking: NODE_COLORS.thinking,
  memory: NODE_COLORS.memory_retrieved,
  blocked: NODE_COLORS.blocked,
  response: LOG_ONLY_COLORS.game_update,
  map: LOG_ONLY_COLORS.map,
  assist: LOG_ONLY_COLORS.assist,
  system: LOG_ONLY_COLORS.system,
};

/** One entry in the Decision Graph timeline (plain scrollable list, no xyflow). */
export interface ReasoningItem {
  id: string;
  type: string;
  content: string;
  room?: string | null;
  memorySource?: MemorySourceKind;
}
