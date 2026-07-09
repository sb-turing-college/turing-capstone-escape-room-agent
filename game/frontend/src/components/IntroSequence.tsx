import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { useGameStore } from "../store/gameStore";

const LINE_FADE_IN_S = 2; // keep in sync with the 2s fade-in in startIntroSequence

/**
 * Full-viewport story text crawl for the Start Screen's "Intro" button
 * (see `startIntroSequence` in gameStore.ts for the timing script).
 * Interruptible at any time via Escape or the close button - both call
 * `skipIntro`, which snaps straight back to the Start Screen.
 *
 * The two lines of a pair each get their own fixed-height slot so that the
 * first line never shifts when the second one fades in below it (Phase 5
 * follow-up, Auftrag Punkt 7).
 */
export default function IntroSequence() {
  const { introVisibleLines, introFadeOutMs, skipIntro } = useGameStore();
  const [first, second] = introVisibleLines;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") skipIntro();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [skipIntro]);

  return (
    <div className="fixed inset-0 z-[900] flex flex-col items-center justify-center gap-6 bg-black px-6 text-center md:gap-8">
      <button
        type="button"
        onClick={skipIntro}
        title="Skip intro (Esc)"
        aria-label="Skip intro"
        className="pixel-btn absolute right-4 top-4 md:right-6 md:top-6"
      >
        ✕
      </button>

      <div className="flex min-h-[3.5rem] items-center justify-center md:min-h-[5rem]">
        <AnimatePresence>
          {first && (
            <motion.p
              key={first}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, transition: { duration: LINE_FADE_IN_S, ease: "easeInOut" } }}
              exit={{ opacity: 0, transition: { duration: introFadeOutMs / 1000, ease: "easeInOut" } }}
              className="max-w-3xl text-xl leading-relaxed text-gray-100 md:text-3xl"
            >
              {first}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      <div className="flex min-h-[3.5rem] items-center justify-center md:min-h-[5rem]">
        <AnimatePresence>
          {second && (
            <motion.p
              key={second}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, transition: { duration: LINE_FADE_IN_S, ease: "easeInOut" } }}
              exit={{ opacity: 0, transition: { duration: introFadeOutMs / 1000, ease: "easeInOut" } }}
              className="max-w-3xl text-xl leading-relaxed text-gray-100 md:text-3xl"
            >
              {second}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
