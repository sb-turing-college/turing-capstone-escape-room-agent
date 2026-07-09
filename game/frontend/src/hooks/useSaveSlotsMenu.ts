import { useCallback, useState } from "react";

import { useGameStore } from "../store/gameStore";
import { ROOM_LABELS } from "../types/game";

export function useSaveSlotsMenu() {
  const { fetchSaveSlots, saveToSlot, setView, slotsLoading, saveSlots, savingSlot } =
    useGameStore();

  const [saveMenuOpen, setSaveMenuOpen] = useState(false);
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null);

  const handleToggleSaveMenu = useCallback(() => {
    setSaveMenuOpen((open) => {
      const opening = !open;
      if (opening) void fetchSaveSlots();
      return opening;
    });
    setSaveFeedback(null);
  }, [fetchSaveSlots]);

  const handleSaveToSlot = useCallback(
    async (slot: number) => {
      try {
        const info = await saveToSlot(slot);
        setSaveFeedback(`Saved to Slot ${slot} (${ROOM_LABELS[info.room]}).`);
      } catch (err) {
        setSaveFeedback(err instanceof Error ? err.message : "Save failed.");
      }
    },
    [saveToSlot],
  );

  const handleRemember = useCallback(() => {
    setSaveMenuOpen(false);
    setView("load");
  }, [setView]);

  return {
    saveMenuOpen,
    saveFeedback,
    slotsLoading,
    saveSlots,
    savingSlot,
    handleToggleSaveMenu,
    handleSaveToSlot,
    handleRemember,
  };
}
