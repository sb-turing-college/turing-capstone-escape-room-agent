import type { GameState, Verb } from "../types/game";
import {
  DIRECTION_LABELS,
  VERBS,
  labelItem,
} from "../types/game";
import { getSecondTargets, getTargetsForVerb } from "../lib/roomTargets";

interface VerbPanelProps {
  game: GameState;
  selectedVerb: Verb | null;
  selectedTarget: string | null;
  codeInput: string;
  loading: boolean;
  onSelectVerb: (verb: Verb) => void;
  onSelectTarget: (target: string) => void;
  onCodeInput: (code: string) => void;
  onSubmit: (command: string) => void;
  onCancel: () => void;
}

const USE_WITH_TARGETS = new Set([
  "brass_key",
  "small_key",
  "rope",
  "hook",
  "grappling_hook",
  "door",
  "lockbox",
  "grate",
]);

function useNeedsWithTarget(target: string): boolean {
  return USE_WITH_TARGETS.has(target);
}

export function buildCommand(
  verb: Verb,
  target: string | null,
  second: string | null,
  codeInput: string,
): string | null {
  if (verb === "go" && target) return `go ${target}`;

  if ((verb === "take" || verb === "examine" || verb === "read") && target) {
    return `${verb} ${target}`;
  }

  if (verb === "use" && target === "safe" && codeInput.trim()) {
    return `use safe ${codeInput.trim().replace(/\s/g, "")}`;
  }

  if (verb === "use" && target && second) {
    return `use ${target} with ${second}`;
  }

  if (verb === "use" && target && !second) {
    return `use ${target}`;
  }

  if (verb === "open" && target) {
    return `open ${target}`;
  }

  return null;
}

export default function VerbPanel({
  game,
  selectedVerb,
  selectedTarget,
  codeInput,
  loading,
  onSelectVerb,
  onSelectTarget,
  onCodeInput,
  onSubmit,
  onCancel,
}: VerbPanelProps) {
  const needsSecond =
    selectedVerb === "use" && selectedTarget && useNeedsWithTarget(selectedTarget);
  const needsCode = selectedVerb === "use" && selectedTarget === "safe";
  const needsConfirm =
    selectedVerb &&
    selectedTarget &&
    !needsSecond &&
    !needsCode &&
    selectedVerb !== "go";

  const primaryTargets = selectedVerb ? getTargetsForVerb(game, selectedVerb) : [];
  const secondTargets =
    selectedVerb === "use" && selectedTarget ? getSecondTargets(game, selectedTarget) : [];

  const handlePrimaryClick = (target: string) => {
    if (selectedVerb === "go") {
      onSubmit(`go ${target}`);
      return;
    }
    // Second click on the same object confirms (SCUMM-style)
    if (selectedTarget === target) {
      onSubmit(buildCommand(selectedVerb!, target, null, codeInput) ?? "");
      return;
    }
    onSelectTarget(target);
  };

  const handleSecondClick = (target: string) => {
    if (selectedVerb !== "use" || !selectedTarget) return;
    // Second click on the same "with" object also confirms
    if (target === selectedTarget) {
      onSubmit(buildCommand("use", selectedTarget, null, codeInput) ?? "");
      return;
    }
    onSubmit(buildCommand("use", selectedTarget, target, codeInput) ?? "");
  };

  const handleVerbClick = (verb: Verb) => {
    onSelectVerb(verb);
  };

  return (
    <div className="pixel-border space-y-3 bg-mm-panel/80 p-3">
      <div className="font-pixel text-[10px] uppercase text-mm-accent">Actions</div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {VERBS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={`pixel-btn ${selectedVerb === id ? "pixel-btn-active" : ""}`}
            disabled={loading}
            onClick={() => handleVerbClick(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {selectedVerb && (
        <div className="space-y-2 border-t border-mm-border pt-3">
          <div className="text-lg text-mm-highlight">
            {selectedVerb.toUpperCase()}
            {selectedTarget ? ` → ${labelItem(selectedTarget)}` : " → choose object"}
          </div>

          {!needsSecond && !needsCode && (
            <div className="flex flex-wrap gap-2">
              {primaryTargets.length === 0 && (
                <span className="text-lg opacity-70">No targets available.</span>
              )}
              {primaryTargets.map((target) => (
                <button
                  key={target}
                  type="button"
                  className={`pixel-btn text-base ${
                    selectedTarget === target ? "pixel-btn-active" : ""
                  }`}
                  disabled={loading}
                  onClick={() => handlePrimaryClick(target)}
                >
                  {selectedVerb === "go" ? DIRECTION_LABELS[target] ?? target : labelItem(target)}
                </button>
              ))}
            </div>
          )}

          {needsSecond && (
            <div className="space-y-2">
              <div className="text-lg">…with:</div>
              <div className="flex flex-wrap gap-2">
                {secondTargets.map((target) => (
                  <button
                    key={target}
                    type="button"
                    className="pixel-btn text-base"
                    disabled={loading}
                    onClick={() => handleSecondClick(target)}
                  >
                    {labelItem(target)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {needsCode && (
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                maxLength={6}
                placeholder="6-digit code"
                value={codeInput}
                className="pixel-border w-40 bg-black/40 px-3 py-2 text-xl outline-none"
                onChange={(e) => onCodeInput(e.target.value.replace(/\D/g, ""))}
              />
              <button
                type="button"
                className="pixel-btn"
                disabled={loading || codeInput.length !== 6}
                onClick={() => onSubmit(buildCommand(selectedVerb, selectedTarget, null, codeInput) ?? "")}
              >
                Enter code
              </button>
            </div>
          )}

          {needsConfirm && selectedTarget && (
            <p className="text-base opacity-70">
              Click <span className="text-mm-highlight">{labelItem(selectedTarget)}</span> again to
              confirm.
            </p>
          )}

          <button type="button" className="pixel-btn text-base opacity-80" onClick={onCancel}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
