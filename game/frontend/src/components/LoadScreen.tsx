import { useEffect } from "react";

import { useGameStore } from "../store/gameStore";
import { ROOM_LABELS } from "../types/game";

export default function LoadScreen() {
  const { saveSlots, slotsLoading, loadingSlot, error, fetchSaveSlots, loadFromSlot, cancelRemember } =
    useGameStore();

  useEffect(() => {
    void fetchSaveSlots();
  }, [fetchSaveSlots]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-mm-bg p-4 md:p-8">
      <header className="text-center">
        <h1 className="font-pixel text-lg text-mm-accent md:text-2xl">Remember</h1>
        <p className="mt-2 font-pixel text-[10px] text-mm-highlight md:text-xs">
          Choose a memory to return to.
        </p>
      </header>

      <div className="pixel-border w-full max-w-md space-y-3 bg-mm-panel/60 p-6">
        {slotsLoading && <p className="text-center text-xl opacity-70">Loading...</p>}

        {!slotsLoading &&
          saveSlots?.map((slot) => (
            <button
              key={slot.slot}
              type="button"
              className="pixel-btn w-full"
              disabled={slot.empty || loadingSlot !== null}
              onClick={() => void loadFromSlot(slot.slot)}
            >
              {loadingSlot === slot.slot
                ? "Loading..."
                : `Slot ${slot.slot}: ${slot.empty ? "Empty" : ROOM_LABELS[slot.room!]}`}
            </button>
          ))}

        {error && <p className="text-center text-lg text-red-300">{error}</p>}
      </div>

      <button type="button" className="pixel-btn" disabled={loadingSlot !== null} onClick={cancelRemember}>
        Back
      </button>
    </div>
  );
}
