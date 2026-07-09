import { useEffect, useRef, type DependencyList } from "react";

const NEAR_BOTTOM_THRESHOLD_PX = 80;

/**
 * Keeps a scrollable container pinned to its bottom as new content arrives,
 * but only while the user is already near the bottom — if they've scrolled
 * up to read something, new events won't yank them back down.
 *
 * Scrolls the container directly (scrollTop assignment), never via
 * `scrollIntoView`, which can otherwise bubble up and jump the whole page.
 */
export function useStickToBottom<T extends HTMLElement>(deps: DependencyList) {
  const containerRef = useRef<T>(null);
  const stickToBottomRef = useRef(true);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distanceFromBottom < NEAR_BOTTOM_THRESHOLD_PX;
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !stickToBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { containerRef, handleScroll };
}
