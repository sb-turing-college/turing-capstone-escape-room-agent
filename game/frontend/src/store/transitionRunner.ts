import type { TransitionOptions, TransitionVisualState } from "./transitions";
import { IDLE_TRANSITION, wait } from "./transitions";

export function makeTransitionRunner(
  set: (partial: Record<string, TransitionVisualState>) => void,
  key: "transition" | "viewTransition",
) {
  return async ({ fadeOutMs, holdMs, fadeInMs, onMidpoint }: TransitionOptions) => {
    set({ [key]: { visible: true, opacity: 1, durationMs: fadeOutMs } });
    await wait(fadeOutMs);
    await wait(holdMs);
    await onMidpoint?.();
    set({ [key]: { visible: true, opacity: 0, durationMs: fadeInMs } });
    await wait(fadeInMs);
    set({ [key]: IDLE_TRANSITION });
  };
}

export { wait, IDLE_TRANSITION, TRANSITION_PRESETS } from "./transitions";
export type { TransitionOptions } from "./transitions";
