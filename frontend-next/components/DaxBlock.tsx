"use client";

import { useMemo, useState } from "react";
import { tokenizeDax } from "@/lib/format";
import { CheckIcon, CopyIcon } from "./Icons";

const TOKEN_CLASS: Record<string, string> = {
  kw: "text-signal-deep font-medium",
  fn: "text-plum",
  str: "text-flag",
  num: "text-flag",
  col: "text-sheet-ink",
  plain: "text-sheet-muted",
};

interface Props {
  dax: string;
  purpose?: string;
}

export default function DaxBlock({ dax, purpose }: Props) {
  const [copied, setCopied] = useState(false);

  const lines = useMemo(() => {
    return dax.split("\n").map((line) => tokenizeDax(line));
  }, [dax]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(dax);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked — the query is still selectable */
    }
  }

  return (
    <figure className="overflow-hidden rounded-card border border-sheet-line bg-sheet-card shadow-card">
      <figcaption className="flex items-center gap-3 border-b border-sheet-line bg-[#FBFCFC] px-3.5 py-2">
        <span className="h-3.5 w-[3px] shrink-0 rounded-full bg-signal" aria-hidden />
        <span className="truncate text-meta text-sheet-muted">
          {purpose || "DAX sent to the semantic model"}
        </span>
        <div className="ml-auto flex items-center gap-3">
          <button
            type="button"
            onClick={copy}
            className="flex items-center gap-1.5 rounded-chip border border-sheet-line px-2 py-1 text-micro text-sheet-muted transition-colors hover:border-signal hover:text-signal-deep"
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </figcaption>

      <div className="scroll-sheet overflow-x-auto">
        <pre className="min-w-full py-2.5 font-mono text-[12.5px] leading-[1.65]">
          {lines.map((tokens, i) => (
            <div key={i} className="flex px-1">
              <span
                aria-hidden
                className="tnum w-9 shrink-0 select-none pr-3 text-right text-[11px] leading-[1.65] text-sheet-line"
              >
                {i + 1}
              </span>
              <code className="whitespace-pre pr-4">
                {tokens.map((t, j) => (
                  <span key={j} className={TOKEN_CLASS[t.type]}>
                    {t.text}
                  </span>
                ))}
              </code>
            </div>
          ))}
        </pre>
      </div>
    </figure>
  );
}
