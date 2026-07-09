import { applyRoomVisited } from "../../lib/mapGraph";
import type { AgentEvent } from "../../types/agent";
import type { AgentStoreGet, AgentStoreSet } from "../agentStoreTypes";

export function createMapActions(set: AgentStoreSet, get: AgentStoreGet) {
  return {
    addMapEvent: (event: AgentEvent) => {
      if (event.type !== "room_visited" || !event.room) return;

      const { mapNodes, mapEdges } = get();
      const { nodes, edges } = applyRoomVisited(mapNodes, mapEdges, {
        room: event.room,
        from: event.from,
        via: event.via,
        label: event.label,
      });
      set({ mapNodes: nodes, mapEdges: edges });
    },
  };
}
