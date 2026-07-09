import { useGameStore } from "../store/gameStore";

/**
 * Popup shown when an `examine`/`take` response carries an `image` (Phase
 * 3c, e.g. the secret book's illustrated pages). Centered, closable via the
 * X button or by taking any further action (the store clears `examineImage`
 * on the next response).
 *
 * The frame sizes itself to the image (`w-fit`/`h-fit` + `max-h`/`max-w` on
 * the `<img>`) instead of a fixed 50%x50% viewport box - a fixed box whose
 * aspect ratio doesn't match the image left large empty panel-colored bars
 * on the sides (Phase 5 follow-up: "viel lila Padding" bug report).
 */
export default function ExamineImageModal() {
  const { examineImage, closeExamineImage } = useGameStore();

  if (!examineImage) return null;

  return (
    <div className="fixed inset-0 z-[997] flex items-center justify-center bg-black/80 p-4">
      <div className="pixel-border relative h-fit w-fit bg-mm-panel p-3">
        <button
          type="button"
          className="pixel-btn absolute right-2 top-2 z-10 px-2 py-0.5 text-lg leading-none"
          onClick={closeExamineImage}
          aria-label="Close"
        >
          X
        </button>
        <img
          src={examineImage}
          alt="Examined item"
          draggable={false}
          className="max-h-[80vh] max-w-[85vw] object-contain"
        />
      </div>
    </div>
  );
}
