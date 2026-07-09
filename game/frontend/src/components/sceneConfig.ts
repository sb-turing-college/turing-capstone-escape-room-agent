import type { GameState, RoomId } from "../types/game";
import { labelItem } from "../types/game";

/**
 * Image-based scene configuration.
 *
 * Backgrounds are empty; every interactable object is a cut-out sprite that is
 * shown/hidden via `visible()` and rendered in its state variant (open/closed)
 * via `src()`. Visibility/state come from the engine (`visible_items`,
 * `object_states`).
 *
 * Coordinates are percentages of the scene; (left, top) = center of the sprite,
 * width = width relative to the scene width (height automatic).
 * scaleY / scaleOrigin – optional vertical stretch (e.g. grate height).
 */

export const ROOM_BG: Record<RoomId, string> = {
  library: "/assets/rooms/library.png",
  parlor: "/assets/rooms/parlor.png",
  lords_office: "/assets/rooms/lords_office.png",
};

const S = "/assets/sprites/";

export interface SpritePlacement {
  id: string;
  label: string;
  left: number;
  top: number;
  width: number;
  scaleY?: number;
  scaleOrigin?: string;
  /** CSS transform, e.g. perspective + rotateY for hinged door swing */
  transform?: string;
  transformOrigin?: string;
  /** Applies a subtle animated "magic warp" ripple (SVG filter defined in
   * RoomScene.tsx). Used for the Unearthly Ladder (Phase 4a): sells it as a
   * conjured rift and hides that its art doesn't perfectly register with the
   * baked-in fireplace behind it. */
  warp?: boolean;
  visible: (g: GameState) => boolean;
  src: (g: GameState) => string;
}

const has = (g: GameState, id: string) => g.visible_items.includes(id);
const state = (g: GameState, key: string) => g.object_states?.[key];

export const ROOM_SPRITES: Record<RoomId, SpritePlacement[]> = {
  library: [
    {
      id: "brass_key",
      label: labelItem("brass_key"),
      left: 14,
      top: 62,
      width: 2.5,
      visible: (g) => has(g, "brass_key"),
      src: () => `${S}brass_key.png`,
    },
    {
      id: "lockbox",
      label: labelItem("lockbox"),
      left: 23.9,
      top: 59.2,
      width: 7.5,
      visible: (g) => state(g, "lockbox") === "open",
      src: () => `${S}lockbox_open.png`,
    },
    {
      id: "lockbox",
      label: labelItem("lockbox"),
      left: 23,
      top: 60,
      width: 7.5,
      visible: (g) => state(g, "lockbox") !== "open",
      src: () => `${S}lockbox_closed.png`,
    },
    {
      id: "note_code",
      label: labelItem("note_code"),
      left: 23.9,
      top: 59.7,
      width: 2,
      visible: (g) => has(g, "note_code") && state(g, "lockbox") === "open",
      src: () => `${S}note.png`,
    },
    {
      id: "door",
      label: labelItem("door"),
      left: 85.5,
      top: 48.3,
      width: 13,
      scaleY: 0.98,
      scaleOrigin: "50% 100%",
      visible: (g) => state(g, "door") !== "open",
      src: () => `${S}door_closed.png`,
    },
    {
      id: "door",
      label: labelItem("door"),
      left: 85.5,
      top: 50.5,
      width: 13,
      scaleY: 0.93,
      scaleOrigin: "100% 0%",
      visible: (g) => state(g, "door") === "open",
      src: () => `${S}door_closed.png`,
      transform: "perspective(900px) rotateY(-78deg)",
      transformOrigin: "100% 50%",
    },
  ],
  parlor: [
    {
      id: "note_memo",
      label: labelItem("note_memo"),
      left: 48,
      top: 38,
      width: 3.5,
      visible: (g) => has(g, "note_memo"),
      src: () => `${S}note.png`,
    },
    {
      id: "small_key",
      label: labelItem("small_key"),
      left: 48,
      top: 38,
      width: 1.32,
      visible: (g) => has(g, "small_key"),
      src: () => `${S}small_key.png`,
    },
    {
      id: "rope",
      label: labelItem("rope"),
      left: 30,
      top: 74,
      width: 6.5,
      visible: (g) => has(g, "rope"),
      src: () => `${S}rope.png`,
    },
    {
      id: "hook",
      label: labelItem("hook"),
      left: 54,
      top: 34,
      width: 5.6,
      visible: (g) => has(g, "hook"),
      src: () => `${S}hook.png`,
    },
    {
      id: "chainsaw",
      label: labelItem("chainsaw"),
      left: 11,
      top: 85,
      width: 16,
      visible: (g) => has(g, "chainsaw"),
      src: () => `${S}chainsaw.png`,
    },
    {
      id: "grate",
      label: labelItem("grate"),
      left: 87,
      top: 59,
      width: 16,
      scaleY: 1.08,
      scaleOrigin: "50% 100%",
      visible: () => true,
      src: () => `${S}grate.png`,
    },
    {
      id: "unearthly_ladder",
      label: labelItem("unearthly_ladder"),
      left: 51.7,
      top: 60,
      width: 30,
      visible: (g) => has(g, "unearthly_ladder"),
      src: () => `${S}unearthly_ladder.png`,
      warp: true,
    },
    {
      id: "hook_on_grate",
      label: labelItem("hook_on_grate"),
      left: 87,
      top: 55,
      width: 6.5,
      visible: (g) => has(g, "hook_on_grate"),
      src: () => `${S}hook_on_grate.png`,
    },
  ],
  lords_office: [
    {
      id: "painting",
      label: labelItem("painting"),
      left: 50,
      top: 34,
      width: 26,
      visible: (g) => state(g, "painting") !== "open",
      src: () => `${S}painting_closed.png`,
    },
    {
      id: "safe",
      label: labelItem("safe"),
      left: 54,
      top: 36,
      width: 17,
      visible: (g) => has(g, "safe") && state(g, "safe") !== "open",
      src: () => `${S}safe.png`,
    },
    {
      id: "safe",
      label: labelItem("safe"),
      left: 59,
      top: 36,
      width: 27,
      visible: (g) => has(g, "safe") && state(g, "safe") === "open",
      src: () => `${S}safe_open_no_book.png`,
    },
    {
      id: "painting",
      label: labelItem("painting"),
      left: 36,
      top: 34,
      width: 18,
      visible: (g) => state(g, "painting") === "open",
      src: () => `${S}painting_open.png`,
    },
    {
      id: "secret_book",
      label: labelItem("secret_book"),
      left: 54.6,
      top: 36.2,
      width: 8.2,
      visible: (g) => has(g, "secret_book"),
      src: () => `${S}secret_book.png`,
    },
  ],
};
