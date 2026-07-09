import { hasThoughtContent } from "../lib/stepLogUtils";
import { memorySourceGraphLabel, type MemorySourceKind } from "../lib/memorySourceLabels";
import type { ReasoningItem } from "../types/agent";
import { NODE_COLORS, ROOM_LABELS } from "../types/agent";

const TYPE_LABELS: Record<string, string> = {
  thought: "THOUGHT",
  action: "ACTION",
  observation: "OBSERVATION",
  memory_retrieved: "MEMORY (retrieved)",
  memory_stored: "MEMORY (stored)",
  thinking: "THINKING",
  blocked: "BLOCKED",
};

function eventLabel(item: {
  type: string;
  memorySource?: MemorySourceKind;
}): string {
  if (item.type === "memory_retrieved") {
    return memorySourceGraphLabel(item.memorySource, false);
  }
  if (item.type === "memory_stored") {
    return memorySourceGraphLabel(item.memorySource, true);
  }
  return TYPE_LABELS[item.type] ?? item.type;
}

type ReasoningGraphProps = {
  items: ReasoningItem[];
  expandedIds: Set<string>;
  collapsedIds: Set<string>;
  onToggleExpanded: (id: string, type: "thought" | "action" | "observation") => void;
};

export function ReasoningGraph({
  items,
  expandedIds,
  collapsedIds,
  onToggleExpanded,
}: ReasoningGraphProps) {
  if (items.length === 0) {
    return (
      <div className="flex min-h-[220px] items-center justify-center rounded-lg border border-purple-900/40 bg-panel/80 p-4">
        <p className="text-xs text-gray-500">No reasoning events to show.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-purple-900/40 bg-panel/80 p-2">
      <div className="space-y-2 pr-1">
        {items.map((item, index) => {
          const isObservation = item.type === "observation";
          const isThought = item.type === "thought";
          const isAction = item.type === "action";
          const isEmptyThought = isThought && !hasThoughtContent(item.content);
          const isCollapsible = isObservation || isThought || isAction;

          let isExpanded: boolean;
          if (isEmptyThought) {
            isExpanded = false;
          } else if (isObservation) {
            isExpanded = expandedIds.has(item.id);
          } else if (isThought || isAction) {
            isExpanded = !collapsedIds.has(item.id);
          } else {
            isExpanded = true;
          }

          const showContent = isExpanded && !isEmptyThought;

          return (
            <div key={item.id} className="relative">
              {index > 0 && <div className="mx-auto h-2 w-px bg-gray-700" />}
              <div
                className="rounded border-l-4 bg-black/30 px-2 py-1.5 text-[11px] leading-snug"
                style={{ borderLeftColor: NODE_COLORS[item.type] ?? "#666" }}
              >
                <div
                  className={`flex items-center gap-2 text-[9px] font-semibold uppercase tracking-wide text-gray-400${
                    showContent ? " mb-1" : ""
                  }`}
                >
                  <span>{eventLabel(item)}</span>
                  {item.room && (
                    <span className="truncate normal-case text-gray-500">
                      {ROOM_LABELS[item.room] ?? item.room}
                    </span>
                  )}
                  {isCollapsible && !isEmptyThought && (
                    <button
                      type="button"
                      onClick={() =>
                        onToggleExpanded(item.id, item.type as "thought" | "action" | "observation")
                      }
                      className="ml-auto normal-case text-accent hover:text-white"
                    >
                      {isExpanded ? "Collapse" : "Expand"}
                    </button>
                  )}
                  {isEmptyThought && (
                    <span className="ml-auto normal-case italic text-gray-500">(empty)</span>
                  )}
                </div>
                {showContent && (
                  <p className="whitespace-pre-wrap break-words font-mono text-gray-200">
                    {item.content}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
