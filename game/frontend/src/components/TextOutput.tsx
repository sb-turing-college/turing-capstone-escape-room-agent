import { useCallback, useEffect, useRef, useState } from "react";

import type { LogEntry } from "../types/game";

interface TextOutputProps {
  logs: LogEntry[];
  loading: boolean;
  /** Shorter log panel when the page uses a viewport-height layout. */
  compact?: boolean;
}

const SCROLL_THRESHOLD = 8;

export default function TextOutput({ logs, loading, compact = false }: TextOutputProps) {
  // Scroll the log container directly (scrollTop assignment) instead of
  // `scrollIntoView`, which can bubble up and jump the *parent* page's
  // scroll position when this component is embedded in an iframe (agent
  // dashboard spectator mode).
  const containerRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(false);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [canScrollDown, setCanScrollDown] = useState(false);

  const updateScrollState = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;

    const overflow = el.scrollHeight - el.clientHeight > SCROLL_THRESHOLD;
    setHasOverflow(overflow);
    setCanScrollDown(overflow && el.scrollHeight - el.scrollTop - el.clientHeight > SCROLL_THRESHOLD);
  }, []);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;

    stickToBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight <= SCROLL_THRESHOLD;
    updateScrollState();
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
    updateScrollState();
  }, [logs, loading, updateScrollState]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver(() => updateScrollState());
    observer.observe(el);
    return () => observer.disconnect();
  }, [updateScrollState]);

  return (
    <div
      className={`pixel-border flex shrink-0 flex-col overflow-hidden bg-black/40 p-3 ${
        compact ? "h-48 md:h-56 lg:h-36" : "h-48 md:h-56"
      }`}
    >
      <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
        <div className="font-pixel text-[10px] uppercase text-mm-accent">Game Log</div>
        {canScrollDown && (
          <span className="rounded bg-black/60 px-1.5 py-0.5 font-pixel text-[8px] uppercase tracking-wide text-mm-accent/90">
            Scroll
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className={`scrollbar-thin h-full min-h-0 pr-2 text-xl leading-relaxed ${
            hasOverflow ? "overflow-y-scroll" : "overflow-y-auto"
          }`}
        >
          {logs.map((entry) => (
            <p
              key={entry.id}
              className={
                entry.type === "command"
                  ? "text-mm-highlight"
                  : entry.type === "error"
                    ? "text-red-400"
                    : entry.type === "system"
                      ? "text-mm-accent"
                      : "text-mm-text"
              }
            >
              {entry.text}
            </p>
          ))}
          {loading && <p className="animate-pulse text-mm-highlight">...</p>}
        </div>
      </div>
    </div>
  );
}
