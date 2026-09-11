"use client";

import { useEffect, useRef } from "react";
import { SendIcon } from "./Icons";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  busy: boolean;
  disabled?: boolean;
}

export default function Composer({ value, onChange, onSubmit, busy, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  return (
    <div className="border-t border-sheet-line bg-sheet-card px-5 py-4 md:px-8">
      <div className="mx-auto max-w-[78ch]">
        <div className="flex items-end gap-2.5 rounded-card border border-sheet-line bg-sheet px-3 py-2.5 transition-shadow focus-within:border-signal focus-within:shadow-card">
          <textarea
            ref={ref}
            rows={1}
            value={value}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit();
              }
            }}
            placeholder="Which category had the highest margin last year?"
            aria-label="Ask the semantic model a question"
            className="max-h-[180px] flex-1 resize-none bg-transparent text-[15px] leading-relaxed text-sheet-ink placeholder:text-sheet-muted focus:outline-none disabled:opacity-50"
          />
          <button
            type="button"
            onClick={onSubmit}
            disabled={busy || disabled || !value.trim()}
            className="flex shrink-0 items-center gap-1.5 rounded-chip bg-signal-deep px-3.5 py-2 text-[13.5px] font-medium text-white transition-colors hover:bg-signal disabled:cursor-not-allowed disabled:bg-sheet-line disabled:text-sheet-muted"
          >
            {busy ? "Working" : "Ask"}
            {!busy && <SendIcon className="h-3.5 w-3.5" />}
          </button>
        </div>

        <p className="mt-2 flex items-center gap-1.5 text-micro text-sheet-muted">
          <kbd className="rounded-[3px] border border-sheet-line bg-sheet-card px-1 py-px font-mono text-[10.5px]">
            Enter
          </kbd>
          to send,
          <kbd className="rounded-[3px] border border-sheet-line bg-sheet-card px-1 py-px font-mono text-[10.5px]">
            Shift + Enter
          </kbd>
          for a new line. Every answer shows the DAX it came from.
        </p>
      </div>
    </div>
  );
}
