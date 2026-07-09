import { useState } from "react";

import { useDisplayRun } from "../hooks/useDisplayRun";
import { GameMapFlow } from "./GameMapFlow";

/** Compact map in the live sidebar — collapsible, expanded by default. */
export function DiscoveredMapPanel({ variant = "default" }: { variant?: "default" | "sidebar" }) {
  const { mapGraph, isRunning, focusedRunId } = useDisplayRun();
  const roomCount = mapGraph.nodes.length;
  const [expanded, setExpanded] = useState(true);
  const roomLabel = `${roomCount} ${roomCount === 1 ? "room" : "rooms"}`;
  const isLive = isRunning && Boolean(focusedRunId);
  const showCounter = Boolean(focusedRunId) && roomCount > 0;

  return (
    <div
      className={`rounded-lg border border-purple-900/40 bg-panel/80 ${variant === "sidebar" ? "p-3" : "p-4"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-baseline gap-2">
          <h2 className="text-sm font-semibold text-accent">Discovered Map</h2>
          {showCounter && (
            <span
              className={`text-[10px] font-normal ${isLive ? "text-green-400" : "text-orange-200"}`}
            >
              {roomLabel}
            </span>
          )}
        </div>
        <button
          type="button"
          className="shrink-0 text-[10px] text-accent hover:text-white"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      {expanded && (
        <div className="mt-1.5">
          <GameMapFlow compact />
        </div>
      )}
    </div>
  );
}
