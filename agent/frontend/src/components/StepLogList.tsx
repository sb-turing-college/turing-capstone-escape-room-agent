import type { Ref, UIEventHandler } from "react";

import { hasThoughtContent } from "../lib/stepLogUtils";
import type { LiveStep } from "../types/agent";
import { STEP_KIND_COLORS } from "../types/agent";

const KIND_LABELS: Record<LiveStep["kind"], string> = {
  command: "ACTION",
  action: "ACTION",
  assist: "ASSIST",
  response: "GAME",
  thought: "THOUGHT",
  memory: "MEMORY",
  system: "SYSTEM",
  map: "MAP",
  detail: "OBSERVATION",
  thinking: "THINKING",
  blocked: "BLOCKED",
};

interface StepLogListProps {
  steps: LiveStep[];
  emptyMessage?: string;
  maxHeightClass?: string;
  /** Grow within a flex column instead of using a fixed max-height. */
  fillHeight?: boolean;
  scrollRef?: Ref<HTMLDivElement>;
  onScroll?: UIEventHandler<HTMLDivElement>;
}

export function StepLogList({
  steps,
  emptyMessage = "No steps to show.",
  maxHeightClass = "max-h-72",
  fillHeight = false,
  scrollRef,
  onScroll,
}: StepLogListProps) {
  const scrollClass = fillHeight
    ? "min-h-0 flex-1 overflow-y-auto"
    : `${maxHeightClass} overflow-y-auto`;

  return (
    <div
      ref={scrollRef}
      onScroll={onScroll}
      className={`${scrollClass} space-y-2 pr-1 text-xs`}
    >
      {steps.length === 0 && <p className="text-gray-500">{emptyMessage}</p>}
      {steps.map((step) => {
        const isEmptyThought = step.kind === "thought" && !hasThoughtContent(step.content);
        return (
          <div
            key={step.id}
            className="rounded border-l-4 bg-black/30 px-2 py-1.5 text-[11px] leading-snug"
            style={{ borderLeftColor: STEP_KIND_COLORS[step.kind] }}
          >
            <div className="mb-0.5 flex items-center gap-2 text-[9px] font-semibold uppercase tracking-wide text-gray-400">
              <span>{KIND_LABELS[step.kind]}</span>
              {step.step != null && <span className="normal-case tabular-nums">#{step.step}</span>}
              {step.room && (
                <span className="truncate normal-case font-normal text-gray-500">{step.room}</span>
              )}
              {isEmptyThought && (
                <span className="ml-auto normal-case font-normal italic text-gray-500">(empty)</span>
              )}
            </div>
            {!isEmptyThought && (
              <p className="whitespace-pre-wrap break-words font-mono text-gray-200">
                {step.content}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export { KIND_LABELS, STEP_KIND_COLORS as KIND_STYLES };
