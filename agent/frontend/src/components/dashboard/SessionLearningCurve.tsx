import type { RunSummary } from "../../types/agent";
import { cumulativeCommandCountForRun } from "../../lib/stepLogUtils";

export const CHART_RUN_LIMIT = 20;
const PANEL_TITLE = "Command Counter";

export type ChartPoint = {
  run: RunSummary;
  runNumber: number;
};

export function runNumberFor(runs: RunSummary[], runId: string): number {
  const index = runs.findIndex((r) => r.run_id === runId);
  return index >= 0 ? runs.length - index : 0;
}

export function buildChartPoints(runs: RunSummary[]): ChartPoint[] {
  return runs
    .filter((r) => r.status !== "running")
    .slice(0, CHART_RUN_LIMIT)
    .reverse()
    .map((run) => ({
      run,
      runNumber: runNumberFor(runs, run.run_id),
    }));
}

function pointFill(run: RunSummary): string {
  if (run.success) return "#34d399";
  if (run.status === "stopped") return "#fb923c";
  return "#f87171";
}

type SessionLearningCurveProps = {
  chartPoints: ChartPoint[];
  runs: RunSummary[];
  hoveredRunId: string | null;
  onHoverRunId: (runId: string | null) => void;
  onSelectRun: (runId: string) => void;
  /** `embedded` — inside Run Control (no panel chrome). */
  variant?: "panel" | "embedded";
};

type LearningCurveChartProps = {
  chartPoints: ChartPoint[];
  runs: RunSummary[];
  hoveredRunId: string | null;
  onHoverRunId: (runId: string | null) => void;
  onSelectRun: (runId: string) => void;
};

function LearningCurveChart({
  chartPoints,
  runs,
  hoveredRunId,
  onHoverRunId,
  onSelectRun,
}: LearningCurveChartProps) {
  const maxCommands = Math.max(
    ...chartPoints.map(({ run }) => cumulativeCommandCountForRun(run, runs)),
    1,
  );
  const padLeft = 26;
  const padRight = 8;
  const padTop = 6;
  const padBottom = 14;
  const width = 400;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = 44;
  const height = padTop + padBottom + plotHeight;

  const pointAt = (index: number, run: RunSummary) => {
    const x = padLeft + (index / Math.max(chartPoints.length - 1, 1)) * plotWidth;
    const y = padTop + plotHeight - (cumulativeCommandCountForRun(run, runs) / maxCommands) * plotHeight;
    return { x, y };
  };

  const yTicks =
    maxCommands <= 5 ? [0, maxCommands] : [0, Math.round(maxCommands / 2), maxCommands];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-28 w-full"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden
    >
      <line
        x1={padLeft}
        y1={padTop}
        x2={padLeft}
        y2={padTop + plotHeight}
        stroke="#4b5563"
        strokeWidth="1"
      />
      <line
        x1={padLeft}
        y1={padTop + plotHeight}
        x2={padLeft + plotWidth}
        y2={padTop + plotHeight}
        stroke="#4b5563"
        strokeWidth="1"
      />
      {yTicks.map((tick) => {
        const y = padTop + plotHeight - (tick / maxCommands) * plotHeight;
        return (
          <g key={tick}>
            <line
              x1={padLeft - 3}
              y1={y}
              x2={padLeft}
              y2={y}
              stroke="#4b5563"
              strokeWidth="1"
            />
            <text
              x={padLeft - 5}
              y={y + 3}
              textAnchor="end"
              className="fill-gray-500 text-[8px]"
            >
              {tick}
            </text>
          </g>
        );
      })}
      <polyline
        fill="none"
        stroke="#7c5cff"
        strokeWidth="1"
        points={chartPoints
          .map(({ run }, index) => {
            const { x, y } = pointAt(index, run);
            return `${x},${y}`;
          })
          .join(" ")}
      />
      {chartPoints.map(({ run, runNumber }, index) => {
        const { x, y } = pointAt(index, run);
        const highlighted = hoveredRunId === run.run_id;
        const fill = pointFill(run);
        return (
          <g
            key={run.run_id}
            className="cursor-pointer"
            onMouseEnter={() => onHoverRunId(run.run_id)}
            onMouseLeave={() => onHoverRunId(null)}
            onClick={() => onSelectRun(run.run_id)}
          >
            <circle cx={x} cy={y} r={6} fill="transparent" />
            <circle
              cx={x}
              cy={y}
              r={highlighted ? 2.5 : 2}
              fill={fill}
              stroke={highlighted ? "#c4b5fd" : "none"}
              strokeWidth={highlighted ? 1 : 0}
            />
            <text
              x={x}
              y={padTop + plotHeight + 11}
              textAnchor="middle"
              className={`text-[8px] ${highlighted ? "fill-gray-200" : "fill-gray-500"}`}
            >
              {runNumber}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function SessionLearningCurve({
  chartPoints,
  runs,
  hoveredRunId,
  onHoverRunId,
  onSelectRun,
  variant = "panel",
}: SessionLearningCurveProps) {
  const chart = chartPoints.length === 0 ? (
    <p className="text-xs text-gray-500">No completed runs yet.</p>
  ) : (
    <LearningCurveChart
      chartPoints={chartPoints}
      runs={runs}
      hoveredRunId={hoveredRunId}
      onHoverRunId={onHoverRunId}
      onSelectRun={onSelectRun}
    />
  );

  if (variant === "embedded") {
    return (
      <div className="flex h-full min-h-[7rem] flex-col">
        <h3 className="mb-1 shrink-0 text-xs font-semibold text-accent">{PANEL_TITLE}</h3>
        <div className="flex min-h-0 flex-1 flex-col justify-center">{chart}</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-purple-900/40 bg-panel/80 p-2.5">
      <h2 className="mb-1 text-sm font-semibold text-accent">{PANEL_TITLE}</h2>
      {chart}
    </div>
  );
}
