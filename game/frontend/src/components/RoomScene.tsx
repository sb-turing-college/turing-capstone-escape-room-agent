import type { CSSProperties } from "react";
import type { GameState, RoomId } from "../types/game";
import { ROOM_LABELS } from "../types/game";
import { ROOM_BG, ROOM_SPRITES, type SpritePlacement } from "./sceneConfig";
import TransitionOverlay from "./TransitionOverlay";

function spriteImgStyle(p: SpritePlacement): CSSProperties | undefined {
  if (p.transform && p.scaleY) return undefined;

  const parts: string[] = [];
  if (p.transform) parts.push(p.transform);
  if (p.scaleY) parts.push(`scaleY(${p.scaleY})`);

  if (!parts.length) return undefined;

  return {
    transform: parts.join(" "),
    transformOrigin: p.transformOrigin ?? p.scaleOrigin ?? "center",
  };
}

function spriteScaleStyle(p: SpritePlacement): CSSProperties | undefined {
  if (!p.scaleY) return undefined;
  return {
    transform: `scaleY(${p.scaleY})`,
    transformOrigin: p.scaleOrigin ?? "center",
  };
}

function spriteSwingStyle(p: SpritePlacement): CSSProperties | undefined {
  if (!p.transform) return undefined;
  return {
    transform: p.transform,
    transformOrigin: p.transformOrigin ?? "center",
  };
}

interface RoomSceneProps {
  game: GameState;
  selectedTarget: string | null;
  onSelectItem: (itemId: string) => void;
  /** Size to fit inside a desktop flex viewport while keeping a 3:2 aspect box. */
  fitViewport?: boolean;
}

export default function RoomScene({
  game,
  selectedTarget,
  onSelectItem,
  fitViewport = false,
}: RoomSceneProps) {
  const room: RoomId = game.room;
  const placements = ROOM_SPRITES[room].filter((p) => p.visible(game));

  return (
    <div
      className={
        fitViewport
          ? "game-scene-fit pixel-border relative max-lg:aspect-[3/2] max-lg:w-full overflow-hidden bg-black select-none"
          : "pixel-border relative aspect-[3/2] w-full overflow-hidden bg-black select-none"
      }
    >
      {/* Hidden SVG filter defs, shared by every `warp`-flagged sprite (Phase
          4a Unearthly Ladder): a slow animated turbulence displacement to
          sell it as a conjured, unstable rift instead of a flat image paste. */}
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
        <defs>
          <filter id="chimney-warp" x="-30%" y="-30%" width="160%" height="160%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.015 0.035"
              numOctaves={2}
              seed={7}
              result="warpNoise"
            >
              <animate
                attributeName="baseFrequency"
                dur="7s"
                values="0.015 0.035;0.022 0.045;0.015 0.035"
                repeatCount="indefinite"
              />
            </feTurbulence>
            <feDisplacementMap
              in="SourceGraphic"
              in2="warpNoise"
              scale={9}
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>

      <img
        src={ROOM_BG[room]}
        alt={ROOM_LABELS[room]}
        className="absolute inset-0 h-full w-full object-cover"
        draggable={false}
      />

      <TransitionOverlay />

      <div className="absolute left-2 top-2 z-30 bg-black/70 px-2 py-1 font-pixel text-[8px] text-mm-accent">
        {ROOM_LABELS[room]}
      </div>

      <img
        src="/assets/ui/compass.png"
        alt="Compass"
        draggable={false}
        className="absolute bottom-[2%] right-[2%] z-30 h-auto w-[11%] opacity-95 drop-shadow-[0_2px_6px_rgba(0,0,0,0.85)]"
      />

      {placements.map((p, idx) => {
        const active = selectedTarget === p.id;
        return (
          <button
            key={`${p.id}-${idx}`}
            type="button"
            title={p.label}
            onClick={() => onSelectItem(p.id)}
            className="group absolute z-20 -translate-x-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-0"
            style={{ left: `${p.left}%`, top: `${p.top}%`, width: `${p.width}%` }}
          >
            {p.transform && p.scaleY ? (
              <div className="w-full" style={spriteSwingStyle(p)}>
                <img
                  src={p.src(game)}
                  alt={p.label}
                  draggable={false}
                  style={spriteScaleStyle(p)}
                  className={`h-auto w-full transition duration-100 ${
                    active
                      ? "scale-105 [filter:drop-shadow(0_0_4px_#f5d76e)_drop-shadow(0_0_2px_#f5d76e)]"
                      : "group-hover:[filter:drop-shadow(0_0_3px_#ffffffcc)]"
                  }`}
                />
              </div>
            ) : (
              <div style={p.warp ? { filter: "url(#chimney-warp)" } : undefined}>
                <img
                  src={p.src(game)}
                  alt={p.label}
                  draggable={false}
                  style={spriteImgStyle(p)}
                  className={`h-auto w-full transition duration-100 ${
                    active
                      ? "scale-105 [filter:drop-shadow(0_0_4px_#f5d76e)_drop-shadow(0_0_2px_#f5d76e)]"
                      : "group-hover:[filter:drop-shadow(0_0_3px_#ffffffcc)]"
                  }`}
                />
              </div>
            )}
            <span
              className={`pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded bg-black/80 px-1.5 py-0.5 text-[11px] text-mm-text opacity-0 transition group-hover:opacity-100 ${
                active ? "opacity-100" : ""
              }`}
            >
              {p.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
