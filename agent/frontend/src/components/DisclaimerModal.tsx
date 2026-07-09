import { useState } from "react";

import { acceptDisclaimer } from "../api/agentApi";
import { actionButtonClass } from "../lib/actionButtonStyles";

const DISCLAIMER_DOC_URL = "/api/agent/disclaimer/doc";

interface DisclaimerModalProps {
  onAccepted: () => void;
}

export function DisclaimerModal({ onAccepted }: DisclaimerModalProps) {
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAccept = async () => {
    setAccepting(true);
    setError(null);
    try {
      await acceptDisclaimer();
      onAccepted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept disclaimer");
    } finally {
      setAccepting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="disclaimer-title"
    >
      <div className="w-full max-w-lg rounded-lg border border-purple-500/60 bg-zinc-950 p-5 shadow-xl">
        <h2 id="disclaimer-title" className="mb-3 text-sm font-semibold text-purple-100">
          Autonomous agent — please read before continuing
        </h2>
        <div className="mb-4 space-y-2 text-[11px] leading-relaxed text-gray-300">
          <p>
            This dashboard runs an <strong className="font-semibold text-gray-100">autonomous AI agent</strong>{" "}
            that calls third-party LLM APIs (OpenRouter). That can incur{" "}
            <strong className="font-semibold text-gray-100">token costs</strong> on your account.
          </p>
          <p>
            The agent acts without manual approval for each step. Outputs may be wrong or incomplete.
            There is <strong className="font-semibold text-gray-100">no warranty</strong> and no guarantee
            of success.
          </p>
          <p>
            Read the full{" "}
            <a
              href={DISCLAIMER_DOC_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-300 underline hover:text-purple-200"
            >
              disclaimer
            </a>{" "}
            before accepting.
          </p>
        </div>
        {error ? (
          <p className="mb-3 text-[11px] text-red-400" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end">
          <button
            type="button"
            className={actionButtonClass}
            onClick={() => void handleAccept()}
            disabled={accepting}
          >
            {accepting ? "Accepting…" : "I accept — enable agent API"}
          </button>
        </div>
      </div>
    </div>
  );
}
