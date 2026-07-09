import { RunAnalysis } from "../RunAnalysis";
import { AgentChatPanel, AgentMemoryPanel } from "./MemoryInterviewPanel";

export function ReviewTab() {
  return (
    <div className="flex h-full min-h-0 flex-col gap-4 lg:grid lg:grid-cols-12 lg:gap-4">
      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:col-span-6 lg:h-full">
        <div className="flex min-h-0 flex-[3] flex-col">
          <AgentChatPanel />
        </div>
        <div className="flex min-h-0 flex-[2] flex-col">
          <AgentMemoryPanel />
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col lg:col-span-6 lg:h-full">
        <RunAnalysis />
      </div>
    </div>
  );
}
