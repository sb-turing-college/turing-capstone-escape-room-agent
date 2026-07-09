import { useEffect, useRef, useState } from "react";

import { actionButtonClass } from "../lib/actionButtonStyles";
import { fetchRunChat, sendRunChatMessage } from "../hooks/useAgentSocket";
import { memorySessionIdForRun } from "../lib/memorySession";
import { useStickToBottom } from "../hooks/useStickToBottom";
import { useAgentStore } from "../store/agentStore";
import type { ChatMessage } from "../types/agent";
import { TypingIndicator } from "./TypingIndicator";

interface RunInterviewChatProps {
  runId: string;
  explorerModel: string;
  /** Fill parent flex column; message history scrolls internally. */
  fillHeight?: boolean;
}

type InterviewMessage = Omit<ChatMessage, "id"> & { id: number | string };

type SendState =
  | { status: "idle" }
  | { status: "sending"; content: string; optimisticId: string }
  | { status: "error"; content: string; errorMessage?: string };

export function RunInterviewChat({ runId, explorerModel, fillHeight = false }: RunInterviewChatProps) {
  const [messages, setMessages] = useState<InterviewMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatSendState, setChatSendState] = useState<SendState>({ status: "idle" });
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savedMessageIds, setSavedMessageIds] = useState<Set<number>>(() => new Set());
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const isSending = chatSendState.status === "sending";

  const { containerRef, handleScroll } = useStickToBottom<HTMLDivElement>([
    messages.length,
    isSending,
  ]);

  useEffect(() => {
    let cancelled = false;
    setInitialLoading(true);
    setError(null);
    setChatSendState({ status: "idle" });
    setMessages([]);
    void fetchRunChat(runId)
      .then((history) => {
        if (!cancelled) setMessages(history);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load chat");
        }
      })
      .finally(() => {
        if (!cancelled) setInitialLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isSending) return;

    const optimisticId = `msg-${Date.now()}`;
    const optimisticMessage: InterviewMessage = {
      id: optimisticId,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    setInput("");
    setError(null);
    setChatSendState({ status: "sending", content: text, optimisticId });

    try {
      const response = await sendRunChatMessage(runId, text);
      setMessages((prev) => [
        ...prev.filter((message) => message.id !== optimisticId),
        response.user_message,
        response.assistant_message,
      ]);
      if (response.memory_saved) {
        setSavedMessageIds((prev) => new Set(prev).add(response.assistant_message.id));
        const runs = useAgentStore.getState().runs;
        const run = runs.find((entry) => entry.run_id === runId);
        const sessionId = run ? memorySessionIdForRun(run, runs) : runId;
        void useAgentStore.getState().refreshMemory(sessionId);
      }
      setChatSendState({ status: "idle" });
    } catch (err) {
      setMessages((prev) => prev.filter((message) => message.id !== optimisticId));
      setInput(text);
      const message = err instanceof Error ? err.message : "Failed to send message";
      setError(message);
      setChatSendState({ status: "error", content: text, errorMessage: message });
    } finally {
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const modelLabel = explorerModel.split("/").pop() ?? explorerModel;
  const showChatHistory = !initialLoading && messages.length > 0;

  return (
    <div className={fillHeight ? "flex min-h-0 flex-1 flex-col" : undefined}>
      {initialLoading && <p className="shrink-0 text-xs text-gray-400">Loading chat history…</p>}
      {error && (
        <p className="mb-2 shrink-0 rounded border border-red-500/40 bg-red-950/30 p-2 text-xs text-red-200">
          {error}
        </p>
      )}

      {(showChatHistory || isSending) && (
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className={
            fillHeight
              ? "mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-0.5"
              : "mb-3 max-h-80 space-y-2 overflow-y-auto pr-0.5"
          }
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`w-fit max-w-[60%] break-words rounded px-3 py-2 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "ml-auto border border-blue-500/40 bg-blue-950/40 text-blue-100"
                  : "mr-auto border border-yellow-500/30 bg-yellow-950/20 text-yellow-50"
              }`}
            >
              <div className="mb-1 text-[10px] text-gray-500">
                {msg.role === "user"
                  ? "You"
                  : msg.content.startsWith("[Interview summary")
                    ? "Summary"
                    : modelLabel}
              </div>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === "assistant" &&
                typeof msg.id === "number" &&
                savedMessageIds.has(msg.id) && (
                  <p className="mt-1 text-[10px] text-purple-300">✓ Saved to agent memory</p>
                )}
            </div>
          ))}
          {isSending && <TypingIndicator label={`${modelLabel} is thinking`} />}
        </div>
      )}

      <div className="flex shrink-0 gap-2">
        <textarea
          ref={inputRef}
          rows={2}
          className="min-h-[2.5rem] flex-1 resize-y rounded border border-gray-700 bg-black/40 px-2 py-1.5 text-xs text-gray-100"
          placeholder="Ask about a decision, puzzle, or dead end…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending || initialLoading}
        />
        <button
          type="button"
          className={`self-end ${actionButtonClass}`}
          onClick={() => void handleSend()}
          disabled={isSending || initialLoading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
