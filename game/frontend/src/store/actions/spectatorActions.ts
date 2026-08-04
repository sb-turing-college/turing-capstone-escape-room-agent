import { ApiError, getGameState } from "../../api/gameApi";
import type { GameState } from "../../types/game";
import { addLog } from "../logUtils";
import type { GameStoreGet, GameStoreSet } from "../gameStoreTypes";

/** Poll while the agent run is live (URL `live=1` or parent postMessage). */
export const SPECTATE_LIVE_POLL_MS = 1500;

let spectatePollId: ReturnType<typeof setInterval> | null = null;
let spectateSessionId: string | null = null;

type Set = GameStoreSet;
type Get = GameStoreGet;

function clearSpectatePoll(): void {
  if (spectatePollId) {
    clearInterval(spectatePollId);
    spectatePollId = null;
  }
}

function tickSpectate(set: Set, sessionId: string): void {
  void getGameState(sessionId)
    .then((next: GameState) => {
      set((state) => {
        if (!state.game) return { game: next };
        const roomChanged = state.game.room !== next.room;
        const textChanged = state.game.text !== next.text;
        if (!roomChanged && !textChanged) return { game: next };
        return {
          game: next,
          logs: addLog(
            addLog(state.logs, "system", "Agent action…"),
            "response",
            next.text,
          ),
        };
      });
    })
    .catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 404) {
        clearSpectatePoll();
        set({ error: "Session no longer available.", loading: false });
      }
    });
}

function startSpectatePoll(set: Set, sessionId: string): void {
  clearSpectatePoll();
  spectatePollId = setInterval(() => tickSpectate(set, sessionId), SPECTATE_LIVE_POLL_MS);
}

export function createSpectatorActions(set: Set, _get: Get) {
  return {
    attachSpectate: async (sessionId: string, options?: { live?: boolean }) => {
      clearSpectatePoll();
      spectateSessionId = sessionId;
      const live = options?.live ?? false;
      set({ loading: true, error: null, isSpectator: true, logs: [] });
      try {
        const game = await getGameState(sessionId);
        set({
          game,
          view: "game",
          loading: false,
          logs: addLog([], "response", game.text),
        });
        if (live) {
          startSpectatePoll(set, sessionId);
        }
      } catch (err) {
        spectateSessionId = null;
        set({
          loading: false,
          error: err instanceof Error ? err.message : "Could not attach to session.",
          isSpectator: false,
        });
      }
    },

    /**
     * Enable/disable live polling without remounting.
     * Used when the agent dashboard signals run start/stop via postMessage.
     */
    setSpectateLive: (live: boolean) => {
      if (!spectateSessionId) return;
      if (live) {
        startSpectatePoll(set, spectateSessionId);
      } else {
        clearSpectatePoll();
      }
    },

    detachSpectate: () => {
      clearSpectatePoll();
      spectateSessionId = null;
      set({ isSpectator: false });
    },
  };
}
