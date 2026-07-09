import gameConstants from "../../../shared/game_constants.json";
import type { GameState, Verb } from "../types/game";

/** Room-specific verb targets not covered by visible_items alone. */
export function getRoomUseExtras(room: string): string[] {
  const extras = gameConstants.room_use_extras as Record<string, string[]>;
  return extras[room] ?? [];
}

export function getTargetsForVerb(game: GameState, verb: Verb): string[] {
  const visible = [...game.visible_items];
  const inventory = [...game.inventory];

  if (verb === "go") {
    const dirs = Object.entries(game.exits)
      .filter(([, status]) => status === "open")
      .map(([dir]) => dir);
    const extras: string[] = [];
    if (game.room === "library" && game.object_states?.door === "open") {
      extras.push("door");
    }
    return [...new Set([...dirs, ...extras])];
  }

  if (verb === "take") {
    return visible.filter((item) => !inventory.includes(item));
  }

  if (verb === "examine" || verb === "read") {
    const roomExtras: string[] = [];
    if (game.room === "library") roomExtras.push("door");
    if (game.room === "parlor") roomExtras.push("grate");
    return [...new Set([...visible, ...inventory, ...roomExtras])];
  }

  if (verb === "use" || verb === "open") {
    return [...new Set([...visible, ...inventory, ...getRoomUseExtras(game.room)])];
  }

  return [];
}

export function getSecondTargets(game: GameState, first: string): string[] {
  return [
    ...new Set(
      [...game.inventory, ...game.visible_items, ...getRoomUseExtras(game.room)].filter(
        (x) => x !== first,
      ),
    ),
  ];
}
