import { fetchMemoryEntries } from "../../api/agentApi";
import type { AgentStoreSet } from "../agentStoreTypes";

export function createMemoryActions(set: AgentStoreSet) {
  return {
    addMemorySnippet: (text: string) =>
      set((state) => {
        if (!text || state.memorySnippets.includes(text)) {
          return state;
        }
        return { memorySnippets: [...state.memorySnippets, text].slice(-5) };
      }),

    clearMemorySnippets: () => set({ memorySnippets: [] }),

    refreshMemory: async (memorySessionId?: string | null) => {
      if (!memorySessionId) {
        set({ memoryEntries: [], memoryCount: 0 });
        return;
      }
      try {
        const entries = await fetchMemoryEntries(memorySessionId);
        set({ memoryEntries: entries, memoryCount: entries.length });
      } catch {
        set({ memoryEntries: [], memoryCount: null });
      }
    },
  };
}
