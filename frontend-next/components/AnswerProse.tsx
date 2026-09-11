"use client";

import { useMemo } from "react";
import { parseMarkdown } from "@/lib/format";

export default function AnswerProse({ text, streaming }: { text: string; streaming?: boolean }) {
  const nodes = useMemo(() => parseMarkdown(text), [text]);
  if (!text.trim()) return null;

  const out: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flush = (key: string) => {
    if (!bullets.length) return;
    out.push(
      <ul key={key} className="my-2 space-y-1 pl-5">
        {bullets.map((html, i) => (
          <li key={i} className="list-disc" dangerouslySetInnerHTML={{ __html: html }} />
        ))}
      </ul>,
    );
    bullets = [];
  };

  nodes.forEach((n, i) => {
    if (n.kind === "li") bullets.push(n.html);
    else {
      flush(`ul-${i}`);
      out.push(<p key={i} className="mb-2 last:mb-0" dangerouslySetInnerHTML={{ __html: n.html }} />);
    }
  });
  flush("ul-end");

  return (
    <div className="max-w-[68ch] font-read text-[17px] leading-[1.62] text-sheet-ink">
      {out}
      {streaming && (
        <span
          aria-hidden
          className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[3px] animate-pulse2 bg-signal"
        />
      )}
    </div>
  );
}
