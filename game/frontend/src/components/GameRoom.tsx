import { useGameStore } from "../store/gameStore";
import { ROOM_LABELS, labelItem } from "../types/game";
import { useCommandInput } from "../hooks/useCommandInput";
import { useHotspotCommand } from "../hooks/useHotspotCommand";
import { useSaveSlotsMenu } from "../hooks/useSaveSlotsMenu";
import RoomScene from "./RoomScene";
import TextOutput from "./TextOutput";
import VerbPanel from "./VerbPanel";

export default function GameRoom() {
  const {
    game,
    logs,
    loading,
    error,
    selectedVerb,
    selectedTarget,
    codeInput,
    executeCommand,
    setSelectedVerb,
    setSelectedTarget,
    setCodeInput,
    clearSelection,
    requestExit,
    isSpectator,
  } = useGameStore();

  const {
    saveMenuOpen,
    saveFeedback,
    slotsLoading,
    saveSlots,
    savingSlot,
    handleToggleSaveMenu,
    handleSaveToSlot,
    handleRemember,
  } = useSaveSlotsMenu();

  const {
    textCommand,
    commandInputRef,
    caretOffset,
    syncCaretPosition,
    handleTextSubmit,
    handleTextChange,
  } = useCommandInput(loading, executeCommand);

  const handleHotspotClick = useHotspotCommand(loading);

  if (!game) return null;

  const compactLayout = !isSpectator;

  const sidebarPanels = (
    <>
      <div className="pixel-border bg-mm-panel/60 p-3">
        <div className="mb-2 font-pixel text-[10px] uppercase text-mm-accent">Inventory</div>
        {game.inventory.length === 0 ? (
          <p className={compactLayout ? "text-lg opacity-70" : "text-xl opacity-70"}>Empty</p>
        ) : (
          <ul className={`space-y-1 ${compactLayout ? "text-lg" : "text-xl"}`}>
            {game.inventory.map((item) => (
              <li key={item}>• {labelItem(item)}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="pixel-border bg-mm-panel/60 p-3">
        <div className="mb-2 font-pixel text-[10px] uppercase text-mm-accent">Visible</div>
        <ul className="flex flex-wrap gap-2">
          {game.visible_items.map((item) => (
            <li
              key={item}
              className={`rounded bg-black/30 px-2 py-1 ${compactLayout ? "text-base" : "text-lg"}`}
            >
              {labelItem(item)}
            </li>
          ))}
        </ul>
      </div>

      <div className="pixel-border bg-mm-panel/60 p-3">
        <div className="mb-2 font-pixel text-[10px] uppercase text-mm-accent">Exits</div>
        <ul className={`space-y-1 ${compactLayout ? "text-lg" : "text-xl"}`}>
          {Object.entries(game.exits).map(([dir, status]) => (
            <li key={dir}>
              {dir}:{" "}
              <span
                className={
                  status === "open"
                    ? "text-green-300"
                    : status === "unlocked"
                      ? "text-yellow-300"
                      : status === "closed"
                        ? "text-red-300"
                        : "text-red-300"
                }
              >
                {status}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {!isSpectator && (
        <>
          <VerbPanel
            game={game}
            selectedVerb={selectedVerb}
            selectedTarget={selectedTarget}
            codeInput={codeInput}
            loading={loading}
            onSelectVerb={setSelectedVerb}
            onSelectTarget={setSelectedTarget}
            onCodeInput={setCodeInput}
            onSubmit={(command) => void executeCommand(command)}
            onCancel={clearSelection}
          />

          <form onSubmit={handleTextSubmit} className="pixel-border space-y-2 bg-mm-panel/60 p-3">
            <label className="font-pixel text-[10px] uppercase text-mm-accent" htmlFor="cmd">
              Text commands &amp; Other actions
            </label>
            <div className="flex gap-2">
              <div className="command-input-wrap relative min-w-0 flex-1">
                <input
                  ref={commandInputRef}
                  id="cmd"
                  type="text"
                  value={textCommand}
                  readOnly={loading}
                  placeholder=" e.g. take brass key"
                  className={`command-input-field pixel-border w-full bg-black/40 px-3 py-2 font-retro caret-transparent outline-none ${
                    compactLayout ? "text-lg" : "text-xl"
                  }`}
                  onFocus={syncCaretPosition}
                  onSelect={syncCaretPosition}
                  onKeyUp={syncCaretPosition}
                  onClick={syncCaretPosition}
                  onChange={(e) => handleTextChange(e.target.value)}
                />
                {!loading && (
                  <span
                    aria-hidden
                    className="command-block-caret"
                    style={{ left: `calc(0.75rem + ${caretOffset}px)` }}
                  />
                )}
              </div>
              <button type="submit" className="pixel-btn" disabled={loading}>
                Send
              </button>
            </div>
          </form>
        </>
      )}
    </>
  );

  return (
    <div
      className={`mx-auto flex w-full max-w-6xl flex-col ${
        compactLayout
          ? "game-room-shell gap-2 lg:h-full lg:min-h-0"
          : isSpectator
            ? "gap-2"
            : "gap-4"
      }`}
    >
      {!isSpectator && (
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="font-pixel text-sm text-mm-accent md:text-base">The Haunted Manor</h1>
            <p className="mt-1 font-pixel text-[9px] text-mm-highlight md:text-[10px]">
              Chapter 0: Anybody... Home?
            </p>
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <button type="button" className="pixel-btn" disabled={loading} onClick={handleToggleSaveMenu}>
                Save memory
              </button>
              {saveMenuOpen && (
                <div className="pixel-border absolute right-0 top-full z-40 mt-2 w-52 space-y-2 bg-mm-panel p-3 text-left">
                  <p className="font-pixel text-[9px] uppercase text-mm-accent">Choose a slot</p>
                  {slotsLoading && <p className="text-lg opacity-70">Loading...</p>}
                  {!slotsLoading &&
                    saveSlots?.map((slot) => (
                      <button
                        key={slot.slot}
                        type="button"
                        className="pixel-btn w-full text-left"
                        disabled={savingSlot !== null}
                        onClick={() => void handleSaveToSlot(slot.slot)}
                      >
                        Slot {slot.slot}: {slot.empty ? "Empty" : ROOM_LABELS[slot.room!]}
                      </button>
                    ))}
                  {saveFeedback && <p className="text-sm text-mm-highlight">{saveFeedback}</p>}
                </div>
              )}
            </div>
            <button type="button" className="pixel-btn" disabled={loading} onClick={handleRemember}>
              Remember
            </button>
            <button type="button" className="pixel-btn" disabled={loading} onClick={requestExit}>
              Flee
            </button>
          </div>
        </header>
      )}

      {error && (
        <div className="pixel-border shrink-0 bg-red-900/40 px-4 py-3 text-xl text-red-200">{error}</div>
      )}

      <div
        className={`grid lg:grid-cols-[2fr_1fr] ${
          compactLayout ? "gap-2 lg:min-h-0 lg:flex-1 lg:overflow-hidden" : "gap-4"
        }`}
      >
        <div
          className={`flex min-w-0 flex-col ${
            compactLayout ? "gap-2 lg:h-full lg:min-h-0 lg:overflow-hidden" : "space-y-4"
          }`}
        >
          <div className={compactLayout ? "game-scene-slot" : undefined}>
            <RoomScene
              game={game}
              selectedTarget={selectedTarget}
              onSelectItem={isSpectator ? () => {} : handleHotspotClick}
              fitViewport={compactLayout}
            />
          </div>
          <TextOutput logs={logs} loading={loading && !isSpectator} compact={compactLayout} />
        </div>

        <aside
          className={
            compactLayout
              ? "flex min-w-0 flex-col lg:min-h-0 lg:overflow-hidden"
              : "space-y-4"
          }
        >
          {compactLayout ? (
            <div className="space-y-2 lg:scrollbar-thin lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pr-1">
              {sidebarPanels}
            </div>
          ) : (
            sidebarPanels
          )}
        </aside>
      </div>
    </div>
  );
}
