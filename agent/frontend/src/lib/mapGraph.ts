import type { Edge, Node } from "@xyflow/react";

import gameConstants from "../shared/game_constants.json";
import type { StoredStep } from "../types/agent";

const ROOM_POSITIONS = gameConstants.room_positions as Record<string, { x: number; y: number }>;

const DEFAULT_ROOM_POSITION = { x: 100, y: 100 };

const ROOM_NODE_STYLE = {
  background: "#1f2937",
  color: "#f3f4f6",
  border: "2px solid #7c5cff",
  borderRadius: 8,
  padding: 10,
  width: 140,
} as const;

export interface RoomVisitedPayload {
  room: string;
  from?: string | null;
  via?: string;
  label?: string;
}

/** Incrementally add a room node and optional edge to an existing graph. */
export function applyRoomVisited(
  nodes: Node[],
  edges: Edge[],
  payload: RoomVisitedPayload,
): { nodes: Node[]; edges: Edge[] } {
  const { room, from, via, label } = payload;
  const nodeId = `room-${room}`;

  let nextNodes = nodes;
  if (!nodes.some((node) => node.id === nodeId)) {
    const pos = ROOM_POSITIONS[room] ?? DEFAULT_ROOM_POSITION;
    nextNodes = [
      ...nodes,
      {
        id: nodeId,
        position: pos,
        data: { label: label ?? room },
        style: { ...ROOM_NODE_STYLE },
      },
    ];
  }

  let nextEdges = edges;
  if (from) {
    const edgeId = `map-${from}-${room}`;
    if (!edges.some((edge) => edge.id === edgeId)) {
      nextEdges = [
        ...edges,
        {
          id: edgeId,
          source: `room-${from}`,
          target: nodeId,
          animated: true,
          label: via ?? "go",
        },
      ];
    }
  }

  return { nodes: nextNodes, edges: nextEdges };
}

export function mapGraphFromSteps(steps: StoredStep[]): { nodes: Node[]; edges: Edge[] } {
  let nodes: Node[] = [];
  let edges: Edge[] = [];

  for (const step of steps) {
    if (step.type !== "room_visited") continue;
    const extra = step.extra ?? {};
    const room = (extra.room as string | undefined) ?? step.room;
    if (!room) continue;

    const result = applyRoomVisited(nodes, edges, {
      room,
      from: extra.from as string | null | undefined,
      via: extra.via as string | undefined,
      label: extra.label as string | undefined,
    });
    nodes = result.nodes;
    edges = result.edges;
  }

  return { nodes, edges };
}
