import { motion } from "framer-motion";

import { useGameStore } from "../store/gameStore";

/**
 * Full-viewport black overlay for cinematic sequences (Phase 2b intro,
 * later Phase 4a ending), driven by `gameStore.viewTransition`. Kept
 * completely independent from the scene-scoped `TransitionOverlay` used by
 * the "go" command flow - see ARCHITECTURE.md 0.4.
 */
export default function ViewTransitionOverlay() {
  const viewTransition = useGameStore((state) => state.viewTransition);

  if (!viewTransition.visible) return null;

  return (
    <motion.div
      aria-hidden="true"
      className="pointer-events-auto fixed inset-0 z-[999] bg-black"
      initial={{ opacity: 0 }}
      animate={{ opacity: viewTransition.opacity }}
      transition={{ duration: viewTransition.durationMs / 1000, ease: "linear" }}
    />
  );
}
