import { useGameStore } from "../store/gameStore";

/**
 * Custom pixel-styled confirmation shown by "Flee" in GameRoom when there are
 * unsaved changes (Phase 2c). Mounted globally so it can overlay the game
 * view regardless of what else is on screen.
 */
export default function ExitConfirmDialog() {
  const { exitConfirmOpen, confirmExit, cancelExit } = useGameStore();

  if (!exitConfirmOpen) return null;

  return (
    <div className="fixed inset-0 z-[998] flex items-center justify-center bg-black/70 p-4">
      <div className="pixel-border max-w-sm space-y-4 bg-mm-panel p-6 text-center">
        <p className="text-xl">Unsaved changes will be lost. Flee anyway?</p>
        <div className="flex justify-center gap-3">
          <button type="button" className="pixel-btn" onClick={cancelExit}>
            Cancel
          </button>
          <button type="button" className="pixel-btn" onClick={confirmExit}>
            Flee
          </button>
        </div>
      </div>
    </div>
  );
}
