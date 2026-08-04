import { useEffect } from "react";

import ChapterTitleCard from "./components/ChapterTitleCard";
import ExamineImageModal from "./components/ExamineImageModal";
import ExitConfirmDialog from "./components/ExitConfirmDialog";
import GameRoom from "./components/GameRoom";
import IntroSequence from "./components/IntroSequence";
import LoadScreen from "./components/LoadScreen";
import StartScreen from "./components/StartScreen";
import ViewTransitionOverlay from "./components/ViewTransitionOverlay";
import { useGameStore } from "./store/gameStore";

const SPECTATE_LIVE_MESSAGE = "capstone-spectate-live";

export default function App() {
  const {
    view,
    game,
    loading,
    error,
    isSpectator,
    startNewGame,
    cinematicTitle,
    cinematicSubtitle,
    attachSpectate,
    detachSpectate,
    setSpectateLive,
  } = useGameStore();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("spectate");
    if (!sessionId) return;
    const live = params.get("live") === "1";
    void attachSpectate(sessionId, { live });
    return () => detachSpectate();
  }, [attachSpectate, detachSpectate]);

  // Agent dashboard toggles live polling without remounting the iframe.
  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { type?: string; live?: boolean } | null;
      if (!data || data.type !== SPECTATE_LIVE_MESSAGE) return;
      setSpectateLive(Boolean(data.live));
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [setSpectateLive]);

  return (
    <>
      <ViewTransitionOverlay />
      <ExitConfirmDialog />
      <ExamineImageModal />

      {view === "start" && <StartScreen />}

      {view === "load" && <LoadScreen />}

      {view === "introStory" && <IntroSequence />}

      {view === "intro" && <ChapterTitleCard title="Chapter 0: Anybody... Home?" />}

      {view === "cinematic" && (
        <ChapterTitleCard title={cinematicTitle} subtitle={cinematicSubtitle} />
      )}

      {view === "game" && (
        <div
          className={
            isSpectator
              ? "bg-mm-bg p-2 md:p-3"
              : "game-play-shell flex flex-col bg-mm-bg p-1 md:p-2"
          }
        >
          {!game && !error && (
            <div className="flex flex-1 items-center justify-center text-2xl text-mm-highlight">
              {loading ? "Loading game..." : "Connecting to backend..."}
            </div>
          )}

          {error && !game && (
            <div className="mx-auto max-w-xl space-y-4 text-center">
              <div className="pixel-border bg-red-900/40 p-6 text-xl text-red-200">{error}</div>
              <p className="text-xl opacity-80">
                Start the backend first:{" "}
                <code className="text-mm-accent">uvicorn main:app --reload --port 8000</code>
              </p>
              <button type="button" className="pixel-btn" onClick={() => void startNewGame()}>
                Try again
              </button>
            </div>
          )}

          {game && <GameRoom />}
        </div>
      )}
    </>
  );
}
