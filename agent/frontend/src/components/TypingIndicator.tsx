import { useEffect, useState } from "react";

interface TypingIndicatorProps {
  label?: string;
}

/** Animated placeholder while the model generates a reply (chat bubble style). */
export function TypingIndicator({ label = "Thinking" }: TypingIndicatorProps) {
  const [dots, setDots] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev % 3) + 1);
    }, 400);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mr-auto w-fit max-w-[60%] break-words rounded border border-yellow-500/30 bg-yellow-950/20 px-3 py-2">
      <div className="flex items-center whitespace-nowrap text-xs text-yellow-100/80">
        <span>{label}</span>
        <span className="inline-block w-[3ch] font-bold">{ ".".repeat(dots) }</span>
      </div>
    </div>
  );
}
