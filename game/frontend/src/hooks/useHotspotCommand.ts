import { useCallback } from "react";

import { useGameStore } from "../store/gameStore";
import { buildCommand } from "../components/VerbPanel";

export function useHotspotCommand(loading: boolean) {
  const {
    selectedVerb,
    selectedTarget,
    codeInput,
    executeCommand,
    setSelectedVerb,
    setSelectedTarget,
  } = useGameStore();

  return useCallback(
    (itemId: string) => {
      if (loading) return;

      const verb = selectedVerb ?? "examine";

      // USE: first object chosen → click second object executes the combination
      if (verb === "use" && selectedTarget && selectedTarget !== itemId) {
        void executeCommand(`use ${selectedTarget} with ${itemId}`);
        return;
      }

      // Click the same object again to confirm (SCUMM-style)
      if (selectedTarget === itemId && selectedVerb) {
        const cmd = buildCommand(selectedVerb, itemId, null, codeInput);
        if (cmd) {
          void executeCommand(cmd);
          return;
        }
      }

      if (!selectedVerb) setSelectedVerb("examine");
      setSelectedTarget(itemId);
    },
    [
      loading,
      selectedVerb,
      selectedTarget,
      codeInput,
      executeCommand,
      setSelectedVerb,
      setSelectedTarget,
    ],
  );
}
