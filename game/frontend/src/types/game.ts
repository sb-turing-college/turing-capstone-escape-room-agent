import gameConstants from "../../../shared/game_constants.json";

export type RoomId = "library" | "parlor" | "lords_office";

export type Verb =
  | "examine"
  | "take"
  | "use"
  | "open"
  | "go"
  | "read";

export interface GameState {
  session_id: string | null;
  text: string;
  room: RoomId;
  visible_items: string[];
  exits: Record<string, string>;
  inventory: string[];
  is_solved: boolean;
  object_states: Record<string, string>;
  available_verbs: string[];
  /** Optional image path shown by `ExamineImageModal` for this turn's response
   * (Phase 3c, e.g. the open book's illustrated pages). `null` most turns. */
  image: string | null;
  /** Set when this turn triggers the cinematic ending (Phase 4a, e.g.
   * "chapter1"). `null` on every other turn. */
  ending: string | null;
}

export interface LogEntry {
  id: string;
  type: "system" | "command" | "response" | "error";
  text: string;
}

/** One of the 3 save slots per browser/`client_id` (Phase 2c). */
export interface SaveSlotInfo {
  slot: number;
  empty: boolean;
  room: RoomId | null;
  updated_at: string | null;
}

export interface SaveActionResult {
  slot: number;
  room: RoomId;
  updated_at: string;
}

export const VERBS: { id: Verb; label: string }[] = [
  { id: "examine", label: "EXAMINE" },
  { id: "read", label: "READ" },
  { id: "take", label: "TAKE" },
  { id: "use", label: "USE" },
  { id: "open", label: "OPEN" },
  { id: "go", label: "GO" },
];

export const ITEM_LABELS: Record<string, string> = gameConstants.item_labels;

export const ROOM_LABELS: Record<RoomId, string> = gameConstants.room_labels as Record<
  RoomId,
  string
>;

export const DIRECTION_LABELS: Record<string, string> = gameConstants.direction_labels;

export function labelItem(itemId: string): string {
  return ITEM_LABELS[itemId] ?? itemId.replace(/_/g, " ");
}
