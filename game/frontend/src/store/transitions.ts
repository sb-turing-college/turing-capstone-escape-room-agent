/**
 * Global fade-transition presets + helpers, shared by the "go" command
 * flow (standard) and cinematic sequences like the intro/ending (Phase 2b/4a).
 */

export interface TransitionOptions {
  fadeOutMs: number;
  holdMs: number;
  fadeInMs: number;
  /** Runs while the screen is fully black, before the fade-in starts. */
  onMidpoint?: () => void | Promise<void>;
}

export interface TransitionVisualState {
  visible: boolean;
  opacity: number;
  durationMs: number;
}

export const TRANSITION_PRESETS = {
  standard: { fadeOutMs: 250, holdMs: 500, fadeInMs: 250 },
  cinematic: { fadeOutMs: 2000, holdMs: 1000, fadeInMs: 2000 },
} as const satisfies Record<string, Omit<TransitionOptions, "onMidpoint">>;

export type TransitionPreset = keyof typeof TRANSITION_PRESETS;

export const IDLE_TRANSITION: TransitionVisualState = {
  visible: false,
  opacity: 0,
  durationMs: 0,
};

export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
