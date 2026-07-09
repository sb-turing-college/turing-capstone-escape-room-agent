import { useEffect, useState } from "react";

import { fetchSpectateSession } from "../hooks/useAgentSocket";
import { useDisplayRun } from "../hooks/useDisplayRun";
import { SpectatorLiveButtons, SpectatorPausePanel } from "./dashboard/GameSpectatorLiveControls";

const GAME_FRONTEND_URL =
  import.meta.env.VITE_GAME_FRONTEND_URL ?? "http://127.0.0.1:5173";

const SPECTATE_SCALE = 0.63;
const SPECTATE_VIEW_HEIGHT = 523;
const SPECTATE_IFRAME_HEIGHT = 830;

type GameSpectatorPanelProps = {
  fillHeight?: boolean;
};

export function GameSpectatorPanel({ fillHeight = false }: GameSpectatorPanelProps) {
  const { focusedRunId, isRunning } = useDisplayRun();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [restored, setRestored] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!focusedRunId) {
      setSessionId(null);
      setRestored(false);
      setError(null);
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    const MAX_ATTEMPTS = 40;

    setLoading(true);
    setError(null);
    setSessionId(null);

    const poll = () => {
      if (cancelled) return;
      void fetchSpectateSession(focusedRunId)
        .then((data) => {
          if (cancelled) return;
          if (data.pending) {
            attempt += 1;
            if (attempt >= MAX_ATTEMPTS) {
              setLoading(false);
              setError("Run did not produce a game session in time.");
              return;
            }
            timeoutId = setTimeout(poll, 1500);
            return;
          }
          setSessionId(data.session_id);
          setRestored(data.restored);
          setLoading(false);
        })
        .catch((err) => {
          if (cancelled) return;
          setSessionId(null);
          setLoading(false);
          setError(err instanceof Error ? err.message : "Could not load game view.");
        });
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [focusedRunId]);

  const iframeSrc = sessionId
    ? `${GAME_FRONTEND_URL}/?spectate=${encodeURIComponent(sessionId)}`
    : null;

  const panelClass = fillHeight
    ? "flex h-full min-h-0 flex-col rounded-lg border border-purple-900/40 bg-panel/80 p-3"
    : "rounded-lg border border-purple-900/40 bg-panel/80 p-3";

  const viewportClass = fillHeight
    ? "relative min-h-0 w-full flex-1 overflow-hidden rounded border border-gray-700 bg-black"
    : "relative w-full overflow-hidden rounded border border-gray-700 bg-black";

  const viewportStyle = fillHeight ? undefined : { height: SPECTATE_VIEW_HEIGHT };

  const emptyViewportClass = fillHeight
    ? "flex min-h-0 flex-1 items-center justify-center rounded border border-gray-800 bg-black/20"
    : "flex items-center justify-center rounded border border-gray-800 bg-black/20";

  const emptyViewportStyle = fillHeight ? undefined : { height: SPECTATE_VIEW_HEIGHT };

  return (
    <div className={panelClass}>
      <div className="mb-2 flex shrink-0 flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-accent">Live Game View</h2>
          {restored && (
            <span className="text-[10px] text-gray-500">restored session</span>
          )}
        </div>
        <SpectatorLiveButtons />
      </div>
      <SpectatorPausePanel />

      {!focusedRunId && (
        <div className={emptyViewportClass} style={emptyViewportStyle}>
          <p className="text-xs text-gray-500">
            Start a run from Sessions, then watch it here.
          </p>
        </div>
      )}

      {focusedRunId && loading && (
        <div className={emptyViewportClass} style={emptyViewportStyle}>
          <p className="text-xs text-gray-400">
            {isRunning
              ? "Waiting for the run to start the game…"
              : "Connecting to game session…"}
          </p>
        </div>
      )}

      {error && (
        <p className="shrink-0 rounded border border-red-500/40 bg-red-950/30 p-2 text-xs text-red-200">
          {error}
        </p>
      )}

      {iframeSrc && !error && (
        <div className={viewportClass} style={viewportStyle}>
          <iframe
            title="Haunted Manor — agent spectate"
            src={iframeSrc}
            className="absolute left-0 top-0 origin-top-left border-0 bg-black"
            style={{
              width: `${100 / SPECTATE_SCALE}%`,
              height: SPECTATE_IFRAME_HEIGHT,
              transform: `scale(${SPECTATE_SCALE})`,
            }}
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      )}
    </div>
  );
}
