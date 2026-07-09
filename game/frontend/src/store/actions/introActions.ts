import { INTRO_LINES } from "../../content/introText";
import { TRANSITION_PRESETS, wait } from "../transitionRunner";
import type { GameStoreGet, GameStoreSet } from "../gameStoreTypes";

export function createIntroActions(set: GameStoreSet, get: GameStoreGet) {
  return {
    startExploreSequence: async () => {
      const { runViewTransition, startNewGame } = get();

      await runViewTransition({
        ...TRANSITION_PRESETS.cinematic,
        fadeOutMs: 1000,
        onMidpoint: () => set({ view: "intro" }),
      });

      await wait(2000);

      await runViewTransition({
        ...TRANSITION_PRESETS.cinematic,
        fadeInMs: 1000,
        onMidpoint: async () => {
          await startNewGame();
          set({ view: "game" });
        },
      });
    },

    playEndingSequence: async () => {
      const { runViewTransition } = get();

      await runViewTransition({
        ...TRANSITION_PRESETS.cinematic,
        onMidpoint: () =>
          set({
            view: "cinematic",
            cinematicTitle: "Chapter 1: What Lies Below",
            cinematicSubtitle: "",
          }),
      });

      await wait(2000);
      set({ cinematicSubtitle: "Coming soon...?" });
      await wait(2000);

      await runViewTransition({
        ...TRANSITION_PRESETS.cinematic,
        onMidpoint: () =>
          set({ cinematicTitle: "End of Demo – Thank you for playing!", cinematicSubtitle: "" }),
      });

      await wait(4000);
      await runViewTransition({
        fadeOutMs: 2000,
        holdMs: 0,
        fadeInMs: 1000,
        onMidpoint: () => set({ view: "start", cinematicTitle: "", cinematicSubtitle: "" }),
      });
    },

    startIntroSequence: async () => {
      const { runViewTransition } = get();
      const runId = get().introRunId + 1;
      set({ introRunId: runId, introVisibleLines: [], introFadeOutMs: 2000 });
      const cancelled = () => get().introRunId !== runId;

      await runViewTransition({
        fadeOutMs: 1000,
        holdMs: 2000,
        fadeInMs: 0,
        onMidpoint: () => {
          if (!cancelled()) set({ view: "introStory" });
        },
      });
      if (cancelled()) return;

      const pairs: Array<[string, string | undefined]> = [];
      for (let i = 0; i < INTRO_LINES.length; i += 2) {
        pairs.push([INTRO_LINES[i], INTRO_LINES[i + 1]]);
      }

      const HOLD_ADJUST_MS: Record<number, number> = {
        0: 500,
        1: 500,
        3: -500,
        4: 2000,
        5: 1000,
        6: 1500,
        7: 1500,
        8: 3000,
      };

      for (let i = 0; i < pairs.length; i++) {
        const [first, second] = pairs[i];
        const firstIdx = i * 2;
        const secondIdx = firstIdx + 1;

        set({ introVisibleLines: [first] });
        await wait(2000 + 4000 + (HOLD_ADJUST_MS[firstIdx] ?? 0));
        if (cancelled()) return;

        if (second) {
          set({ introVisibleLines: [first, second] });
          await wait(2000 + 4000 + (HOLD_ADJUST_MS[secondIdx] ?? 0));
          if (cancelled()) return;
        }

        set({ introFadeOutMs: 2000, introVisibleLines: [] });
        await wait(2000);
        if (cancelled()) return;
      }

      await runViewTransition({
        fadeOutMs: 0,
        holdMs: 1000,
        fadeInMs: 2000,
        onMidpoint: () => set({ view: "start" }),
      });
    },

    skipIntro: () => {
      set((state) => ({
        introRunId: state.introRunId + 1,
        introVisibleLines: [],
        view: "start",
      }));
    },
  };
}
