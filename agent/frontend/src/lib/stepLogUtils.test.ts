import { describe, expect, it } from "vitest";

import { applyRoomVisited, mapGraphFromSteps } from "./mapGraph";
import {
  filterStoredSteps,
  formatSegmentCommandBudget,
  gameStateFromSteps,
  isSyntheticThought,
  liveStepFromEvent,
  reasoningItemsFromSteps,
  resolveRunMaxSteps,
  stepTypeCounts,
  summarizeObservation,
  thoughtDisplayContent,
} from "./stepLogUtils";
import type { StoredStep } from "../types/agent";

describe("summarizeObservation", () => {
  it("formats JSON observations compactly", () => {
    const raw = JSON.stringify({
      room: "library",
      inventory: ["brass_key"],
      visible_items: ["lockbox"],
      ending: null,
    });
    expect(summarizeObservation(raw)).toContain("room=library");
    expect(summarizeObservation(raw)).toContain("brass_key");
  });

  it("falls back to truncated text for non-JSON", () => {
    const long = "x".repeat(200);
    expect(summarizeObservation(long)).toHaveLength(180);
  });
});

describe("thought helpers", () => {
  it("detects legacy synthetic thoughts", () => {
    expect(isSyntheticThought("→ go north\n→ examine door")).toBe(true);
    expect(isSyntheticThought("Planning my next move")).toBe(false);
  });

  it("strips synthetic content for display", () => {
    expect(thoughtDisplayContent("→ step")).toBe("");
    expect(thoughtDisplayContent("real thought")).toBe("real thought");
  });
});

describe("liveStepFromEvent", () => {
  it("maps action events to command steps", () => {
    const step = liveStepFromEvent({
      type: "action",
      content: "send_command: take brass key",
      step: 3,
      room: "library",
    });
    expect(step?.kind).toBe("command");
    expect(step?.content).toBe("take brass key");
  });

  it("maps ask_human actions to assist steps, not commands", () => {
    const step = liveStepFromEvent({
      type: "action",
      content: "ask_human: Where is the safe?",
      step: 4,
      room: "library",
    });
    expect(step?.kind).toBe("assist");
    expect(step?.content).toBe("Where is the safe?");
  });
});

describe("filterStoredSteps and counts", () => {
  const steps: StoredStep[] = [
    {
      step_number: 1,
      type: "action",
      content: "send_command: look",
      room: "library",
      timestamp: "2026-01-01T00:00:00Z",
    },
    {
      step_number: 2,
      type: "thought",
      content: "hmm",
      room: "library",
      timestamp: "2026-01-01T00:00:01Z",
    },
    {
      step_number: 3,
      type: "room_visited",
      content: "",
      room: "parlor",
      timestamp: "2026-01-01T00:00:02Z",
      extra: { room: "parlor", from: "library" },
    },
  ];

  it("filters by category", () => {
    expect(filterStoredSteps(steps, "commands")).toHaveLength(1);
    expect(filterStoredSteps(steps, "map")).toHaveLength(1);
  });

  it("counts step types", () => {
    expect(stepTypeCounts(steps)).toEqual({ action: 1, thought: 1, room_visited: 1 });
  });
});

describe("gameStateFromSteps", () => {
  it("returns latest game_update state", () => {
    const steps: StoredStep[] = [
      {
        step_number: 1,
        type: "game_update",
        content: "old",
        room: "library",
        timestamp: "t1",
        extra: { visible_items: [], inventory: [], exits: {}, is_solved: false },
      },
      {
        step_number: 2,
        type: "game_update",
        content: "current",
        room: "parlor",
        timestamp: "t2",
        extra: {
          visible_items: ["grate"],
          inventory: ["rope"],
          exits: { north: "library" },
          is_solved: false,
          ending: null,
        },
      },
    ];
    const state = gameStateFromSteps(steps);
    expect(state?.room).toBe("parlor");
    expect(state?.text).toBe("current");
    expect(state?.inventory).toEqual(["rope"]);
  });
});

describe("applyRoomVisited", () => {
  it("adds a node with position from game_constants", () => {
    const { nodes, edges } = applyRoomVisited([], [], {
      room: "library",
      label: "The Library",
    });
    expect(nodes).toHaveLength(1);
    expect(nodes[0].position).toEqual({ x: 0, y: 0 });
    expect(nodes[0].data).toEqual({ label: "The Library" });
    expect(edges).toHaveLength(0);
  });

  it("skips duplicate nodes and edges", () => {
    let nodes: ReturnType<typeof applyRoomVisited>["nodes"] = [];
    let edges: ReturnType<typeof applyRoomVisited>["edges"] = [];

    ({ nodes, edges } = applyRoomVisited(nodes, edges, {
      room: "library",
      label: "The Library",
    }));
    ({ nodes, edges } = applyRoomVisited(nodes, edges, {
      room: "library",
      label: "The Library",
    }));
    ({ nodes, edges } = applyRoomVisited(nodes, edges, {
      room: "parlor",
      from: "library",
      via: "go",
      label: "The Parlor",
    }));
    ({ nodes, edges } = applyRoomVisited(nodes, edges, {
      room: "parlor",
      from: "library",
      via: "go",
      label: "The Parlor",
    }));

    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);
    expect(edges[0].id).toBe("map-library-parlor");
  });

  it("uses fallback position for unknown rooms", () => {
    const { nodes } = applyRoomVisited([], [], { room: "unknown_room" });
    expect(nodes[0].position).toEqual({ x: 100, y: 100 });
  });
});

describe("mapGraphFromSteps", () => {
  it("builds nodes and edges from room_visited steps", () => {
    const steps: StoredStep[] = [
      {
        step_number: 1,
        type: "room_visited",
        content: "",
        room: "library",
        timestamp: "t1",
        extra: { room: "library", label: "The Library", from: null, via: "start" },
      },
      {
        step_number: 2,
        type: "room_visited",
        content: "",
        room: "parlor",
        timestamp: "t2",
        extra: { room: "parlor", label: "The Parlor", from: "library", via: "go" },
      },
    ];
    const { nodes, edges } = mapGraphFromSteps(steps);
    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);
    expect(edges[0].source).toBe("room-library");
    expect(edges[0].target).toBe("room-parlor");
  });
});

describe("reasoningItemsFromSteps", () => {
  it("filters reasoning types and cleans thoughts", () => {
    const steps: StoredStep[] = [
      {
        step_number: 1,
        type: "thought",
        content: "→ synthetic",
        room: "library",
        timestamp: "t1",
      },
      {
        step_number: 2,
        type: "action",
        content: "send_command: look",
        room: "library",
        timestamp: "t2",
      },
    ];
    const items = reasoningItemsFromSteps(steps);
    expect(items).toHaveLength(2);
    expect(items[0].content).toBe("");
    expect(items[1].type).toBe("action");
  });
});

describe("formatSegmentCommandBudget", () => {
  it("shows segment over max when budget is known", () => {
    expect(formatSegmentCommandBudget(6, 12)).toBe("6/12");
  });

  it("omits total when segment equals cumulative", () => {
    expect(formatSegmentCommandBudget(6, 12, 6)).toBe("6/12");
  });

  it("appends total only for continue segments", () => {
    expect(formatSegmentCommandBudget(3, 12, 9)).toBe("3/12 · total 9");
  });

  it("shows plain count for legacy runs without max_steps", () => {
    expect(formatSegmentCommandBudget(6, null)).toBe("6");
    expect(formatSegmentCommandBudget(6, null, 6)).toBe("6");
  });

  it("shows total for legacy continue segments", () => {
    expect(formatSegmentCommandBudget(3, null, 9)).toBe("3 · total 9");
  });
});

describe("resolveRunMaxSteps", () => {
  it("prefers live WebSocket budget during an active run", () => {
    expect(
      resolveRunMaxSteps({
        run: { max_steps: 12 },
        isLiveRun: true,
        liveRunMaxSteps: 10,
      }),
    ).toBe(10);
  });

  it("uses persisted run budget for historical review", () => {
    expect(
      resolveRunMaxSteps({
        run: { max_steps: 12 },
        isLiveRun: false,
        liveRunMaxSteps: 10,
      }),
    ).toBe(12);
  });

  it("returns null for legacy runs without persisted budget", () => {
    expect(
      resolveRunMaxSteps({
        run: { max_steps: null },
        isLiveRun: false,
        liveRunMaxSteps: 10,
      }),
    ).toBeNull();
  });
});
