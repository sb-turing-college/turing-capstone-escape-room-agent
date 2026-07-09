/**
 * Story text for the Start Screen's "Intro" button (`frontend/src/content/introText.ts`).
 *
 * Displayed two lines at a time by `IntroSequence` / `startIntroSequence`
 * (gameStore.ts): line N fades in, 2s later line N+1 fades in below it, both
 * are held another 2s, then fade out together before the next pair starts.
 */
export const INTRO_LINES: string[] = [
  "You wake up, your head spinning with memories gone as soon as they pop up...",
  "...Lying on a bed of grass, moonshine above, a soothing wind whistles through bare trees...",
  "...How long have you been asleep? Why are you here?",
  "Where are you? Who are you?",
  "As you look up, your gaze catches a mysterious old manor. It feels strangely familiar...",
  "...but when you spot its door wide open, a deep horror overcomes you.",
  "You try to remember, but it is futile. Nothing comes, only emptiness.",
  "There is only one thing you know: Behind that door you will find your answers.",
  "As you scrape together your last remnants of courage, you get up and start your journey into the forgotten...",
];
