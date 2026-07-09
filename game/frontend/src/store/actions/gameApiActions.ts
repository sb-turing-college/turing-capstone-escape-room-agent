import {
  ApiError,
  createGame,
  getSaveSlots,
  loadGame,
  saveGame,
  sendAction,
} from "../../api/gameApi";
import { getClientId } from "../../lib/clientId";
import { addLog } from "../logUtils";
import { TRANSITION_PRESETS } from "../transitionRunner";
import type { GameStoreGet, GameStoreSet } from "../gameStoreTypes";

export function createGameApiActions(set: GameStoreSet, get: GameStoreGet) {
  return {
    startNewGame: async () => {
      set({ loading: true, error: null, logs: [], selectedVerb: null, selectedTarget: null, codeInput: "" });
      try {
        const game = await createGame();
        set({
          game,
          logs: addLog([], "response", game.text),
          loading: false,
          dirty: false,
          examineImage: null,
        });
      } catch (err) {
        set({
          loading: false,
          error: err instanceof Error ? err.message : "Could not start the game.",
        });
      }
    },

    executeCommand: async (command: string) => {
      const { game, runTransition, playEndingSequence } = get();
      if (!game?.session_id || !command.trim()) return;

      const trimmed = command.trim();
      const sessionId = game.session_id;
      const prevRoom = game.room;
      set({ loading: true, error: null });

      try {
        const next = await sendAction(sessionId, trimmed);

        if (next.ending) {
          set({ loading: false, dirty: true });
          await playEndingSequence();
          return;
        }

        const applyResult = () =>
          set((state) => ({
            game: next,
            logs: addLog(addLog(state.logs, "command", `> ${trimmed}`), "response", next.text),
            loading: false,
            dirty: true,
            selectedVerb: null,
            selectedTarget: null,
            codeInput: "",
            examineImage: next.image,
          }));

        if (next.room !== prevRoom) {
          await runTransition({ ...TRANSITION_PRESETS.standard, onMidpoint: applyResult });
        } else {
          applyResult();
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          try {
            const fresh = await createGame();
            set((state) => ({
              game: fresh,
              loading: false,
              dirty: false,
              examineImage: null,
              selectedVerb: null,
              selectedTarget: null,
              codeInput: "",
              logs: addLog(
                addLog(state.logs, "system", "--- Session expired, started a new game ---"),
                "response",
                fresh.text,
              ),
            }));
            return;
          } catch {
            // fall through
          }
        }
        set((state) => ({
          loading: false,
          error: err instanceof Error ? err.message : "Command failed.",
          logs: addLog(state.logs, "error", err instanceof Error ? err.message : "Error"),
        }));
      }
    },
  };
}

export function createSaveLoadActions(set: GameStoreSet, get: GameStoreGet) {
  return {
    fetchSaveSlots: async () => {
      set({ slotsLoading: true, error: null });
      try {
        const saveSlots = await getSaveSlots(getClientId());
        set({ saveSlots, slotsLoading: false });
      } catch (err) {
        set({
          slotsLoading: false,
          error: err instanceof Error ? err.message : "Could not load saves.",
        });
      }
    },

    saveToSlot: async (slot: number) => {
      const { game } = get();
      if (!game?.session_id) throw new Error("No active game to save.");

      set({ savingSlot: slot });
      try {
        const info = await saveGame(game.session_id, slot, getClientId());
        set((state) => ({
          dirty: false,
          savingSlot: null,
          saveSlots: state.saveSlots
            ? state.saveSlots.map((s) =>
                s.slot === slot ? { ...s, empty: false, room: info.room, updated_at: info.updated_at } : s,
              )
            : state.saveSlots,
        }));
        return info;
      } catch (err) {
        set({ savingSlot: null });
        throw err;
      }
    },

    loadFromSlot: async (slot: number) => {
      const { runViewTransition } = get();
      set({ loadingSlot: slot, error: null });

      await runViewTransition({
        ...TRANSITION_PRESETS.standard,
        onMidpoint: async () => {
          try {
            const fresh = await createGame();
            if (!fresh.session_id) throw new Error("Failed to create a session for loading.");
            const loaded = await loadGame(fresh.session_id, slot, getClientId());
            set({
              game: loaded,
              logs: addLog([], "response", loaded.text),
              dirty: false,
              examineImage: null,
              view: "game",
              selectedVerb: null,
              selectedTarget: null,
              codeInput: "",
            });
          } catch (err) {
            set({ error: err instanceof Error ? err.message : "Could not load this save." });
          } finally {
            set({ loadingSlot: null });
          }
        },
      });
    },

    requestExit: () => {
      if (!get().dirty) {
        set({
          view: "start",
          game: null,
          logs: [],
          dirty: false,
          exitConfirmOpen: false,
          examineImage: null,
        });
        return;
      }
      set({ exitConfirmOpen: true });
    },

    confirmExit: () =>
      set({
        view: "start",
        game: null,
        logs: [],
        dirty: false,
        exitConfirmOpen: false,
        examineImage: null,
      }),

    cancelExit: () => set({ exitConfirmOpen: false }),
  };
}
