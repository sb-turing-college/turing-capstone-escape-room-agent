import { AgentQuestionModal } from "./GameSpectatorLiveControls";
import { DecisionGraphColumn } from "../DecisionGraphColumn";
import { DiscoveredMapPanel } from "../DiscoveredMapPanel";
import { GameSpectatorPanel } from "../GameSpectatorPanel";

export function LiveTab() {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <AgentQuestionModal />
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 xl:grid-cols-12 xl:items-stretch">
        <div className="flex min-h-0 flex-col xl:col-span-7">
          <GameSpectatorPanel fillHeight />
        </div>

        <div className="flex min-h-0 flex-col gap-4 xl:col-span-5">
          <div className="shrink-0">
            <DiscoveredMapPanel variant="sidebar" />
          </div>
          <div className="flex min-h-0 flex-1 flex-col">
            <DecisionGraphColumn />
          </div>
        </div>
      </div>
    </div>
  );
}
