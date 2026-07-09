import { useState } from "react";
import { motion } from "framer-motion";

import { useGameStore } from "../store/gameStore";

const A = "/assets/start/";

interface DriftingCloudProps {
  top: number;
  width: number;
  /** Drift speed in percent of scene width per second. */
  speed: number;
  /** Left position (%) of the very first pass; later passes always re-enter off-screen left. */
  firstStartLeft: number;
  waitSeconds: number;
  zIndexClass: string;
  /** Vertical squash factor (1 = untouched, 0.85 = 15% flatter), anchored to the top edge. */
  squashY?: number;
}

/**
 * A cloud layer that drifts left -> right across the scene, fully exits,
 * waits `waitSeconds`, then re-enters from off-screen left and repeats.
 * Uses a `key` remount per cycle so each pass starts instantly at its
 * `initial` position with no leftover transition from the previous pass.
 */
function DriftingCloud({ top, width, speed, firstStartLeft, waitSeconds, zIndexClass, squashY = 1 }: DriftingCloudProps) {
  const [cycle, setCycle] = useState(0);
  const startLeft = cycle === 0 ? firstStartLeft : -width;
  const duration = (100 - startLeft) / speed;

  return (
    <motion.img
      key={cycle}
      src={`${A}clouds.png`}
      alt=""
      draggable={false}
      className={`absolute h-auto ${zIndexClass}`}
      style={{
        width: `${width}%`,
        top: `${top}%`,
        transform: squashY !== 1 ? `scaleY(${squashY})` : undefined,
        transformOrigin: "top",
      }}
      initial={{ left: `${startLeft}%` }}
      animate={{ left: "100%" }}
      transition={{ duration, ease: "linear" }}
      onAnimationComplete={() => {
        window.setTimeout(() => setCycle((c) => c + 1), waitSeconds * 1000);
      }}
    />
  );
}

export default function StartScreen() {
  const { startExploreSequence, startIntroSequence, setView } = useGameStore();
  const [fleeHint, setFleeHint] = useState(false);
  // Guards against a double-click firing two overlapping cinematic
  // sequences (the component stays mounted for ~2s before "view" flips
  // away from "start", unlike the old instant setView("game")).
  const [exploring, setExploring] = useState(false);
  const [introStarting, setIntroStarting] = useState(false);

  const handleExplore = () => {
    if (exploring) return;
    setExploring(true);
    void startExploreSequence();
  };

  const handleRemember = () => {
    setView("load");
  };

  const handleFlee = () => {
    setFleeHint(true);
    window.close();
  };

  const handleIntro = () => {
    if (introStarting) return;
    setIntroStarting(true);
    void startIntroSequence().finally(() => setIntroStarting(false));
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-mm-bg p-4 md:p-8">
      <header className="text-center">
        <h1 className="font-pixel text-lg text-mm-accent md:text-2xl">The Haunted Manor</h1>
      </header>

      <div className="pixel-border relative aspect-[3/2] w-full max-w-4xl overflow-hidden bg-black select-none">
        <img
          src={`${A}manor_night.png`}
          alt="The Haunted Manor at night"
          className="absolute inset-0 h-full w-full object-cover"
          draggable={false}
        />

        <motion.img
          src={`${A}tree.png`}
          alt="Bare tree, foreground"
          draggable={false}
          className="absolute z-10 h-auto origin-bottom"
          style={{ left: "0%", top: "28%", width: "24%" }}
          animate={{ rotate: [-1.05, 1.05, -1.05] }}
          transition={{ duration: 5.4, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.img
          src={`${A}tree.png`}
          alt="Bare tree, distant"
          draggable={false}
          className="absolute z-10 h-auto origin-bottom"
          style={{ left: "60%", top: "49%", width: "13.6%" }}
          animate={{ rotate: [1.05, -1.05, 1.05] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.img
          src={`${A}moon.png`}
          alt="Moon"
          draggable={false}
          className="absolute z-10 h-auto"
          style={{ left: "74%", top: "6%", width: "8.8%" }}
          animate={{ opacity: [1, 1, 0.85, 1, 1] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", times: [0, 0.35, 0.5, 0.65, 1] }}
        />

        <DriftingCloud
          top={10}
          width={37.4}
          speed={2.8}
          firstStartLeft={33}
          waitSeconds={5}
          zIndexClass="z-20"
          squashY={0.85}
        />
        <DriftingCloud top={3} width={19.8} speed={3.7} firstStartLeft={0} waitSeconds={5} zIndexClass="z-20" />

        {/* Static cutout of the chimney, re-drawn above the clouds so drifting
            clouds appear to pass behind it instead of in front. */}
        <img
          src={`${A}chimney_overlay.png`}
          alt=""
          draggable={false}
          className="absolute z-[25] h-auto"
          style={{ left: "16.47%", top: "8.79%", width: "5.14%" }}
        />

        <div className="absolute z-30" style={{ left: "18.5%", top: "9%", width: "4.7%" }}>
          <motion.div
            className="relative w-full origin-bottom"
            animate={{ rotate: [0, 0, 3, -2, 0, 0] }}
            transition={{ duration: 6, repeat: Infinity, times: [0, 0.4, 0.45, 0.5, 0.55, 1] }}
          >
            <img src={`${A}crow.png`} alt="A crow" draggable={false} className="h-auto w-full" />
            <motion.div
              className="absolute aspect-square rounded-full bg-[#0c0c14]"
              style={{ left: "18%", top: "8%", width: "6%" }}
              animate={{ opacity: [0, 0, 1, 0, 0] }}
              transition={{ duration: 4, repeat: Infinity, times: [0, 0.92, 0.95, 0.98, 1] }}
            />
          </motion.div>
        </div>

        <div className="absolute right-3 top-1/2 z-30 flex -translate-y-1/2 flex-col gap-3 md:right-6 md:gap-4">
          <div className="pixel-border flex flex-col gap-2 bg-black/70 p-3 md:gap-3 md:p-4">
            <button type="button" className="pixel-btn" disabled={exploring} onClick={handleExplore}>
              Explore
            </button>
            <button type="button" className="pixel-btn" onClick={handleRemember}>
              Remember
            </button>
            <button type="button" className="pixel-btn" onClick={handleFlee}>
              Flee
            </button>

            {fleeHint && (
              <p className="max-w-[10rem] text-center text-[11px] leading-snug text-mm-highlight opacity-90">
                You may simply close this tab to flee.
              </p>
            )}
          </div>

          <div className="pixel-border flex flex-col gap-2 bg-black/70 p-3 md:gap-3 md:p-4">
            <button type="button" className="pixel-btn" disabled={introStarting} onClick={handleIntro}>
              Intro
            </button>
            <button type="button" className="pixel-btn opacity-60" disabled title="Coming soon">
              Credits
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
