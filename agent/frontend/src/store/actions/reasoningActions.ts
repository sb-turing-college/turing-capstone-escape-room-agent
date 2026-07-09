import { thoughtDisplayContent } from "../../lib/stepLogUtils";
import type { AgentEvent, LiveStep, ReasoningItem } from "../../types/agent";
import type { AgentStoreGet, AgentStoreSet } from "../agentStoreTypes";

let reasoningCounter = 0;

export function resetReasoningCounter(): void {
  reasoningCounter = 0;
}

export function createReasoningActions(set: AgentStoreSet, get: AgentStoreGet) {
  return {
    addReasoningEvent: (event: AgentEvent) => {
      if (
        ![
          "thought",
          "action",
          "observation",
          "memory_retrieved",
          "memory_stored",
          "blocked",
        ].includes(event.type)
      ) {
        return;
      }
      reasoningCounter += 1;
      const item: ReasoningItem = {
        id: `n-${reasoningCounter}`,
        type: event.type,
        content:
          event.type === "thought"
            ? thoughtDisplayContent(event.content)
            : (event.content ?? ""),
        room: event.room,
        memorySource: event.memory_source,
      };
      set({ reasoningItems: [...get().reasoningItems, item] });
    },

    addLiveStep: (step: LiveStep) =>
      set({ liveSteps: [...get().liveSteps, step], lastEventAt: Date.now() }),

    touchLastEvent: () => set({ lastEventAt: Date.now() }),
  };
}
