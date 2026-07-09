import { useEffect } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useDisplayRun } from "../hooks/useDisplayRun";

function FitViewOnRoomChange({ nodeCount }: { nodeCount: number }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (nodeCount > 0) {
      void fitView({ padding: 0.15, duration: 250 });
    }
  }, [nodeCount, fitView]);

  return null;
}

function GameMapFlowInner({ compact = false }: { compact?: boolean }) {
  const { mapGraph } = useDisplayRun();
  const { nodes, edges } = mapGraph;
  const heightClass = compact ? "h-[180px]" : "h-[280px]";
  const emptyMinClass = compact ? "min-h-[120px]" : "min-h-[220px]";

  if (nodes.length === 0) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg border border-purple-900/40 bg-panel/80 p-4 ${emptyMinClass}`}
      >
        <p className="text-xs text-gray-500">No rooms discovered yet.</p>
      </div>
    );
  }

  return (
    <div className={`discovered-map-flow ${heightClass} rounded-lg border border-purple-900/40 bg-panel/80`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <FitViewOnRoomChange nodeCount={nodes.length} />
        <Background gap={20} color="#334155" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export function GameMapFlow({ compact = false }: { compact?: boolean }) {
  return (
    <ReactFlowProvider>
      <GameMapFlowInner compact={compact} />
    </ReactFlowProvider>
  );
}
