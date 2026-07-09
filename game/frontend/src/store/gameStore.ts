import { create } from "zustand";

import { createGameApiActions, createSaveLoadActions } from "./actions/gameApiActions";
import { createIntroActions } from "./actions/introActions";
import { createSpectatorActions } from "./actions/spectatorActions";
import { IDLE_TRANSITION, makeTransitionRunner } from "./transitionRunner";
import type { AppView, GameStore } from "./gameStoreTypes";

export type { AppView } from "./gameStoreTypes";

export const useGameStore = create<GameStore>((set, get) => ({
  view: "start",
  game: null,
  logs: [],
  loading: false,
  error: null,
  selectedVerb: null,
  selectedTarget: null,
  codeInput: "",
  transition: IDLE_TRANSITION,
  viewTransition: IDLE_TRANSITION,
  dirty: false,
  saveSlots: null,
  slotsLoading: false,
  savingSlot: null,
  loadingSlot: null,
  exitConfirmOpen: false,
  examineImage: null,
  cinematicTitle: "",
  cinematicSubtitle: "",
  introVisibleLines: [],
  introFadeOutMs: 2000,
  introRunId: 0,
  isSpectator: false,

  setView: (view: AppView) => set({ view }),

  cancelRemember: () => {
    set({ view: get().game ? "game" : "start", error: null });
  },

  runTransition: makeTransitionRunner(set, "transition"),
  runViewTransition: makeTransitionRunner(set, "viewTransition"),

  setSelectedVerb: (verb) => set({ selectedVerb: verb, selectedTarget: null, codeInput: "" }),
  setSelectedTarget: (target) => set({ selectedTarget: target }),
  setCodeInput: (code) => set({ codeInput: code }),
  clearSelection: () => set({ selectedVerb: null, selectedTarget: null, codeInput: "" }),
  closeExamineImage: () => set({ examineImage: null }),

  ...createGameApiActions(set, get),
  ...createSaveLoadActions(set, get),
  ...createIntroActions(set, get),
  ...createSpectatorActions(set),
}));
