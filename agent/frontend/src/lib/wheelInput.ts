import { useCallback, useEffect, useRef } from "react";

export function stepNumberOnWheel(
  deltaY: number,
  value: number,
  min: number,
  max: number,
  step = 1,
): number {
  const delta = deltaY < 0 ? step : -step;
  return Math.min(max, Math.max(min, value + delta));
}

export function stepSelectOnWheel(
  deltaY: number,
  value: string,
  options: readonly string[],
): string {
  if (options.length <= 1) return value;
  const idx = options.indexOf(value);
  const base = idx >= 0 ? idx : 0;
  const nextIdx =
    deltaY < 0
      ? (base - 1 + options.length) % options.length
      : (base + 1) % options.length;
  return options[nextIdx] ?? value;
}

function findSelect(el: HTMLElement): HTMLSelectElement | null {
  return el instanceof HTMLSelectElement ? el : el.querySelector("select");
}

function shouldHandleWheel(el: HTMLElement): boolean {
  // Hover-only: avoid changing a focused field while the pointer is over another
  // control (each hook listens on document; focus + hover on different fields
  // would otherwise both match).
  const field = el.closest("label") ?? el;
  return field.matches(":hover");
}

function bindSelectOpenTracking(
  select: HTMLSelectElement,
  openRef: { current: boolean },
): () => void {
  const markOpen = () => {
    openRef.current = true;
  };
  const markClosed = () => {
    openRef.current = false;
  };
  const onKeyUp = (event: KeyboardEvent) => {
    if (event.key === "Escape") markClosed();
  };

  select.addEventListener("mousedown", markOpen);
  select.addEventListener("change", markClosed);
  select.addEventListener("blur", markClosed);
  select.addEventListener("keyup", onKeyUp);

  return () => {
    select.removeEventListener("mousedown", markOpen);
    select.removeEventListener("change", markClosed);
    select.removeEventListener("blur", markClosed);
    select.removeEventListener("keyup", onKeyUp);
  };
}

/**
 * Mouse wheel on a field — only while the pointer hovers that control (or its
 * wrapping `<label>`). Skips interception while a native select list is open.
 */
export function useWheelControl<T extends HTMLElement>(
  onWheel: (event: WheelEvent) => void,
  enabled = true,
) {
  const onWheelRef = useRef(onWheel);
  onWheelRef.current = onWheel;
  const elementRef = useRef<T | null>(null);
  const selectOpenRef = useRef(false);
  const unbindSelectRef = useRef<(() => void) | null>(null);

  const setRef = useCallback((node: T | null) => {
    unbindSelectRef.current?.();
    unbindSelectRef.current = null;
    selectOpenRef.current = false;
    elementRef.current = node;

    if (!node) return;
    const select = findSelect(node);
    if (select) {
      unbindSelectRef.current = bindSelectOpenTracking(select, selectOpenRef);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const listener = (event: WheelEvent) => {
      const el = elementRef.current;
      if (!el || !shouldHandleWheel(el)) return;

      const select = findSelect(el);
      if (select && selectOpenRef.current) return;

      event.preventDefault();
      event.stopPropagation();
      onWheelRef.current(event);
    };

    document.addEventListener("wheel", listener, { passive: false, capture: true });
    return () => document.removeEventListener("wheel", listener, { capture: true });
  }, [enabled]);

  useEffect(
    () => () => {
      unbindSelectRef.current?.();
    },
    [],
  );

  return setRef;
}
