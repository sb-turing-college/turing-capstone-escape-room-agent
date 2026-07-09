import { ApiError, getGameState } from "../../api/gameApi";
import type { GameState } from "../../types/game";
import { addLog } from "../logUtils";
import type { GameStoreSet } from "../gameStoreTypes";

let spectatePollId: ReturnType<typeof setInterval> | null = null;

type Set = GameStoreSet;

export function createSpectatorActions(set: Set) {
  return {
    attachSpectate: async (sessionId: string) => {
      if (spectatePollId) {
        clearInterval(spectatePollId);
        spectatePollId = null;
      }
      set({ loading: true, error: null, isSpectator: true, logs: [] });
      try {
        const game = await getGameState(sessionId);
        set({
          game,
          view: "game",
          loading: false,
          logs: addLog([], "response", game.text),
        });

        spectatePollId = setInterval(() => {
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
                if (spectatePollId) clearInterval(spectatePollId);
                spectatePollId = null;
                set({ error: "Session no longer available.", loading: false });
              }
            });
        }, 1500);
      } catch (err) {
        set({
          loading: false,
          error: err instanceof Error ? err.message : "Could not attach to session.",
          isSpectator: false,
        });
      }
    },

    detachSpectate: () => {
      if (spectatePollId) {
        clearInterval(spectatePollId);
        spectatePollId = null;
      }
      set({ isSpectator: false });
    },
  };
}
