import { motion } from "framer-motion";

import { useGameStore } from "../store/gameStore";

/**
 * Black overlay covering only its positioned parent (the room-scene panel),
 * driven by `gameStore.transition`. Opacity and duration are set imperatively
 * by `runTransition()`, so this component only has to render whatever the
 * store currently says. Everything outside the scene panel (text log,
 * inventory, exits, verbs) is intentionally NOT covered - it hard-switches
 * to the new content the instant the fade-in starts, see `runTransition()`.
 *
 * Mounted inside `RoomScene.tsx`, whose wrapper div is already
 * `relative overflow-hidden`, so `absolute inset-0` here clips to that panel.
 */
export default function TransitionOverlay() {
  const transition = useGameStore((state) => state.transition);

  if (!transition.visible) return null;

  return (
    <motion.div
      aria-hidden="true"
      className="pointer-events-auto absolute inset-0 z-40 bg-black"
      initial={{ opacity: 0 }}
      animate={{ opacity: transition.opacity }}
      transition={{ duration: transition.durationMs / 1000, ease: "linear" }}
    />
  );
}
