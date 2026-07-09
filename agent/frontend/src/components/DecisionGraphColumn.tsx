import { useEffect, useMemo, useState, type CSSProperties } from "react";

import { ReasoningGraph } from "./ReasoningGraph";
import { useDisplayRun } from "../hooks/useDisplayRun";
import { hasThoughtContent, liveSendCommandCount, formatSegmentCommandBudget, cumulativeCommandCountForRun, resolveRunMaxSteps } from "../lib/stepLogUtils";
import { useStickToBottom } from "../hooks/useStickToBottom";
import { useAgentStore } from "../store/agentStore";
import { NODE_COLORS } from "../types/agent";

const LIVE_COUNTER_CLASS = "text-[10px] font-normal text-green-400";
const FINISHED_COUNTER_CLASS = "text-[10px] font-normal text-orange-200";

type CoreEventType = "thought" | "action" | "observation";
type BulkExpansionState = "expanded" | "collapsed" | "mixed";

const CORE_EVENT_FILTERS: { id: CoreEventType; label: string }[] = [
  { id: "thought", label: "Thought" },
  { id: "action", label: "Action" },
  { id: "observation", label: "Observation" },
];

const CORE_EVENT_TYPES = new Set<CoreEventType>(["thought", "action", "observation"]);

function toggleSetMember<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

function getBulkExpansionState(
  type: CoreEventType,
  ids: string[],
  expandedIds: Set<string>,
  collapsedIds: Set<string>,
): BulkExpansionState {
  if (ids.length === 0) return "collapsed";

  if (type === "observation") {
    const expandedCount = ids.filter((id) => expandedIds.has(id)).length;
    if (expandedCount === 0) return "collapsed";
    if (expandedCount === ids.length) return "expanded";
    return "mixed";
  }

  const collapsedCount = ids.filter((id) => collapsedIds.has(id)).length;
  if (collapsedCount === 0) return "expanded";
  if (collapsedCount === ids.length) return "collapsed";
  return "mixed";
}

function IconExpandAll({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m7 6 5 5 5-5" />
      <path d="m7 13 5 5 5-5" />
    </svg>
  );
}

function IconCollapseAll({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m7 11 5-5 5 5" />
      <path d="m7 18 5-5 5 5" />
    </svg>
  );
}

type EventTypeFilterGroupProps = {
  type: CoreEventType;
  label: string;
  active: boolean;
  typeIds: string[];
  bulkState: BulkExpansionState;
  onToggleFilter: () => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
};

function EventTypeFilterGroup({
  type,
  label,
  active,
  typeIds,
  bulkState,
  onToggleFilter,
  onExpandAll,
  onCollapseAll,
}: EventTypeFilterGroupProps) {
  const typeColor = NODE_COLORS[type];
  const bulkDisabled = !active || typeIds.length === 0;
  const isMixed = bulkState === "mixed";

  const segmentStyle = (selected: boolean): CSSProperties | undefined => {
    if (bulkDisabled || isMixed || !selected) return undefined;
    return { color: typeColor };
  };

  return (
    <div className="flex shrink-0 items-stretch gap-0.5">
      <button
        type="button"
        className={`rounded border border-gray-700 border-l-4 bg-black/30 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
          active
            ? ""
            : "border-l-gray-700 text-gray-400 hover:bg-gray-800/50 hover:text-gray-200"
        }`}
        style={
          active
            ? { borderLeftColor: typeColor, color: typeColor }
            : undefined
        }
        aria-pressed={active}
        onClick={onToggleFilter}
      >
        {label}
      </button>
      <div
        role="radiogroup"
        aria-label={`${label} detail level`}
        className="flex overflow-hidden rounded border border-gray-700 bg-black/30"
      >
        <button
          type="button"
          role="radio"
          aria-checked={!bulkDisabled && bulkState === "expanded"}
          aria-label={`Expand all ${label.toLowerCase()} entries`}
          title="Expand all"
          disabled={bulkDisabled}
          className={`flex items-center justify-center px-1.5 py-1 transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${
            bulkDisabled
              ? "text-gray-600"
              : isMixed
                ? "text-gray-600 hover:bg-gray-800/50 hover:text-gray-400"
                : bulkState === "expanded"
                  ? ""
                  : "text-gray-500 hover:bg-gray-800/50 hover:text-gray-300"
          }`}
          style={segmentStyle(bulkState === "expanded")}
          onClick={onExpandAll}
        >
          <IconExpandAll />
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={!bulkDisabled && bulkState === "collapsed"}
          aria-label={`Collapse all ${label.toLowerCase()} entries`}
          title="Collapse all"
          disabled={bulkDisabled}
          className={`flex items-center justify-center border-l border-gray-700 px-1.5 py-1 transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${
            bulkDisabled
              ? "text-gray-600"
              : isMixed
                ? "text-gray-600 hover:bg-gray-800/50 hover:text-gray-400"
                : bulkState === "collapsed"
                  ? ""
                  : "text-gray-500 hover:bg-gray-800/50 hover:text-gray-300"
          }`}
          style={segmentStyle(bulkState === "collapsed")}
          onClick={onCollapseAll}
        >
          <IconCollapseAll />
        </button>
      </div>
    </div>
  );
}

export function DecisionGraphColumn() {
  const { reasoningItems, isRunning, focusedRunId, displaySteps } = useDisplayRun();
  const liveRunMaxSteps = useAgentStore((s) => s.liveRunMaxSteps);
  const runs = useAgentStore((s) => s.runs);
  const runId = useAgentStore((s) => s.runId);
  const [enabledTypes, setEnabledTypes] = useState<Set<CoreEventType>>(
    () => new Set(CORE_EVENT_TYPES),
  );
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => new Set());

  const filteredItems = useMemo(
    () =>
      reasoningItems.filter(
        (item): item is typeof item & { type: CoreEventType } =>
          CORE_EVENT_TYPES.has(item.type as CoreEventType) &&
          enabledTypes.has(item.type as CoreEventType),
      ),
    [reasoningItems, enabledTypes],
  );

  const idsByType = useMemo(() => {
    const thought: string[] = [];
    const action: string[] = [];
    const observation: string[] = [];
    for (const item of reasoningItems) {
      if (item.type === "thought") {
        if (hasThoughtContent(item.content)) thought.push(item.id);
      } else if (item.type === "action") {
        action.push(item.id);
      } else if (item.type === "observation") {
        observation.push(item.id);
      }
    }
    return { thought, action, observation };
  }, [reasoningItems]);

  const { containerRef, handleScroll } = useStickToBottom<HTMLDivElement>([
    filteredItems.length,
  ]);

  const commandCount = liveSendCommandCount(displaySteps);
  const focusedRun = focusedRunId
    ? runs.find((entry) => entry.run_id === focusedRunId)
    : undefined;
  const isLiveFocused = isRunning && runId === focusedRunId;
  const maxSteps = resolveRunMaxSteps({
    run: focusedRun,
    isLiveRun: isLiveFocused,
    liveRunMaxSteps,
  });
  const totalCommandCount =
    focusedRun != null
      ? cumulativeCommandCountForRun(
          focusedRun,
          runs,
          isLiveFocused ? commandCount : undefined,
        )
      : commandCount;
  const commandBudget = formatSegmentCommandBudget(
    commandCount,
    maxSteps,
    totalCommandCount,
  );
  const isLive = isRunning && Boolean(focusedRunId);
  const showCommands = Boolean(focusedRunId) && commandCount > 0;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      const atTop = el.scrollTop <= 0;
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1;
      if ((e.deltaY > 0 && atBottom) || (e.deltaY < 0 && atTop)) {
        e.preventDefault();
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [containerRef]);

  const handleToggleExpanded = (id: string, type: CoreEventType) => {
    if (type === "observation") {
      setExpandedIds((prev) => toggleSetMember(prev, id));
    } else {
      setCollapsedIds((prev) => toggleSetMember(prev, id));
    }
  };

  const expandAllOfType = (type: CoreEventType) => {
    const ids = idsByType[type];
    if (type === "observation") {
      setExpandedIds((prev) => {
        const next = new Set(prev);
        for (const id of ids) next.add(id);
        return next;
      });
    } else {
      setCollapsedIds((prev) => {
        const next = new Set(prev);
        for (const id of ids) next.delete(id);
        return next;
      });
    }
  };

  const collapseAllOfType = (type: CoreEventType) => {
    const ids = idsByType[type];
    if (type === "observation") {
      setExpandedIds((prev) => {
        const next = new Set(prev);
        for (const id of ids) next.delete(id);
        return next;
      });
    } else {
      setCollapsedIds((prev) => {
        const next = new Set(prev);
        for (const id of ids) next.add(id);
        return next;
      });
    }
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain xl:pr-1"
    >
      <div className="sticky top-0 z-10 mb-2 bg-panel/95 pb-1 backdrop-blur-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 shrink items-baseline gap-2">
            <h2 className="text-sm font-semibold text-accent">Decision Graph</h2>
            {showCommands && (
              <span
                className={`whitespace-nowrap ${isLive ? LIVE_COUNTER_CLASS : FINISHED_COUNTER_CLASS}`}
              >
                commands {commandBudget}
              </span>
            )}
          </div>
          <div className="flex shrink-0 flex-nowrap items-center gap-1.5 overflow-x-auto">
            {CORE_EVENT_FILTERS.map((filter) => (
              <EventTypeFilterGroup
                key={filter.id}
                type={filter.id}
                label={filter.label}
                active={enabledTypes.has(filter.id)}
                typeIds={idsByType[filter.id]}
                bulkState={getBulkExpansionState(
                  filter.id,
                  idsByType[filter.id],
                  expandedIds,
                  collapsedIds,
                )}
                onToggleFilter={() =>
                  setEnabledTypes((prev) => toggleSetMember(prev, filter.id))
                }
                onExpandAll={() => expandAllOfType(filter.id)}
                onCollapseAll={() => collapseAllOfType(filter.id)}
              />
            ))}
          </div>
        </div>
      </div>
      <ReasoningGraph
        items={filteredItems}
        expandedIds={expandedIds}
        collapsedIds={collapsedIds}
        onToggleExpanded={handleToggleExpanded}
      />
    </div>
  );
}
