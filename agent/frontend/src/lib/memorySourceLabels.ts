export const MEMORY_SOURCE = {
  AGENT_CHAT: "agent_chat",
  IN_GAME_REFLECTION: "in_game_reflection",
  FALLBACK_SUMMARY: "fallback_summary",
} as const;

export type MemorySourceKind =
  | (typeof MEMORY_SOURCE)[keyof typeof MEMORY_SOURCE]
  | "interview"
  | "run_summary"
  | "agent_reflection";

/** Map legacy Chroma metadata to canonical source keys. */
export function normalizeMemorySource(
  source: string | null | undefined,
): (typeof MEMORY_SOURCE)[keyof typeof MEMORY_SOURCE] {
  switch (source) {
    case "interview":
    case MEMORY_SOURCE.AGENT_CHAT:
      return MEMORY_SOURCE.AGENT_CHAT;
    case "agent_reflection":
    case MEMORY_SOURCE.IN_GAME_REFLECTION:
      return MEMORY_SOURCE.IN_GAME_REFLECTION;
    case "run_summary":
    case MEMORY_SOURCE.FALLBACK_SUMMARY:
      return MEMORY_SOURCE.FALLBACK_SUMMARY;
    default:
      return MEMORY_SOURCE.FALLBACK_SUMMARY;
  }
}

/** User-facing label in Review memory cards (lowercase). */
export function memorySourceDisplayLabel(source: string | null | undefined): string {
  switch (normalizeMemorySource(source)) {
    case MEMORY_SOURCE.AGENT_CHAT:
      return "agent chat";
    case MEMORY_SOURCE.IN_GAME_REFLECTION:
      return "in-game reflection";
    case MEMORY_SOURCE.FALLBACK_SUMMARY:
      return "fallback summary";
  }
}

/** Uppercase label in the live Decision Graph memory events. */
export function memorySourceGraphLabel(
  source: MemorySourceKind | undefined,
  stored: boolean,
): string {
  switch (normalizeMemorySource(source)) {
    case MEMORY_SOURCE.AGENT_CHAT:
      return stored ? "AGENT CHAT (stored)" : "AGENT CHAT";
    case MEMORY_SOURCE.IN_GAME_REFLECTION:
      return stored ? "IN-GAME REFLECTION (stored)" : "IN-GAME REFLECTION";
    case MEMORY_SOURCE.FALLBACK_SUMMARY:
      return stored ? "FALLBACK SUMMARY (stored)" : "FALLBACK SUMMARY";
  }
}
