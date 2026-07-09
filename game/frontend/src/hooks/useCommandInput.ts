import { useCallback, useEffect, useRef, useState } from "react";

export function useCommandInput(
  loading: boolean,
  executeCommand: (command: string) => void | Promise<void>,
) {
  const [textCommand, setTextCommand] = useState("");
  const commandInputRef = useRef<HTMLInputElement>(null);
  const [caretOffset, setCaretOffset] = useState(0);

  const syncCaretPosition = useCallback(() => {
    const input = commandInputRef.current;
    if (!input) return;
    const style = window.getComputedStyle(input);
    const before = input.value.slice(0, input.selectionStart ?? 0);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    setCaretOffset(ctx.measureText(before).width);
  }, []);

  const focusCommandInput = useCallback(() => {
    commandInputRef.current?.focus({ preventScroll: true });
    requestAnimationFrame(() => {
      syncCaretPosition();
      requestAnimationFrame(syncCaretPosition);
    });
  }, [syncCaretPosition]);

  useEffect(() => {
    focusCommandInput();
  }, [focusCommandInput]);

  useEffect(() => {
    if (!loading) focusCommandInput();
  }, [loading, focusCommandInput]);

  useEffect(() => {
    syncCaretPosition();
  }, [textCommand, syncCaretPosition]);

  const handleTextSubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      if (!textCommand.trim() || loading) {
        focusCommandInput();
        return;
      }
      void executeCommand(textCommand);
      setTextCommand("");
      focusCommandInput();
    },
    [textCommand, loading, executeCommand, focusCommandInput],
  );

  const handleTextChange = useCallback(
    (value: string) => {
      setTextCommand(value);
      requestAnimationFrame(syncCaretPosition);
    },
    [syncCaretPosition],
  );

  return {
    textCommand,
    commandInputRef,
    caretOffset,
    syncCaretPosition,
    handleTextSubmit,
    handleTextChange,
  };
}
