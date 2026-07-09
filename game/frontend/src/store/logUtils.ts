import type { LogEntry } from "../types/game";

let logCounter = 0;

export function addLog(
  logs: LogEntry[],
  type: LogEntry["type"],
  text: string,
): LogEntry[] {
  return [...logs, { id: `${Date.now()}-${logCounter++}`, type, text }];
}
