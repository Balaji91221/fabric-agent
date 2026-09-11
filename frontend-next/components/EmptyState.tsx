"use client";

import type { ModelSchema } from "@/lib/types";

const STAGES = [
  { title: "Reads the model", body: "Tables, columns and measures, straight from the semantic model." },
  { title: "Writes the DAX", body: "One read-only query, shown to you before the answer." },
  { title: "Explains the rows", body: "The numbers in context, with the query left on screen." },
];

function starters(schema: ModelSchema | null): string[] {
  const measures = new Set((schema?.measures ?? []).map((m) => m.name));
  const pool = [
    { q: "Total sales by category, biggest first", need: "Total Sales" },
    { q: "Top 5 countries by margin in 2024", need: "Margin" },
    { q: "How did sales grow year over year?", need: "Sales YoY %" },
    { q: "Which channel sells the most units?", need: "Units Sold" },
  ].filter((p) => !measures.size || measures.has(p.need));

  return pool.length ? pool.map((p) => p.q) : ["What can this model tell me?"];
}

export default function EmptyState({
  schema,
  onAsk,
}: {
  schema: ModelSchema | null;
  onAsk: (q: string) => void;
}) {
  return (
    <div className="animate-rise mx-auto max-w-[78ch] pt-6">
      <h2 className="max-w-[22ch] font-read text-[34px] leading-[1.15] text-sheet-ink md:text-[40px]">
        Ask a question. Check the query. Then trust the number.
      </h2>
      <p className="mt-3 max-w-[58ch] text-[15px] leading-relaxed text-sheet-muted">
        This agent has read-only access to{" "}
        <span className="text-sheet-ink">{schema?.name ?? "one semantic model"}</span>. It writes the
        DAX itself and leaves it on screen next to the result, so nothing has to be taken on faith.
      </p>

      <ol className="mt-8 grid gap-px overflow-hidden rounded-card border border-sheet-line bg-sheet-line sm:grid-cols-3">
        {STAGES.map((s, i) => (
          <li key={s.title} className="bg-sheet-card p-4">
            <span className="tnum font-mono text-micro text-signal-deep">{i + 1}</span>
            <h3 className="mt-1.5 text-[14px] font-medium text-sheet-ink">{s.title}</h3>
            <p className="mt-1 text-meta leading-snug text-sheet-muted">{s.body}</p>
          </li>
        ))}
      </ol>

      <h3 className="mb-2.5 mt-9 text-meta font-medium text-sheet-muted">Start with one of these</h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {starters(schema).map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onAsk(q)}
            className="group rounded-card border border-sheet-line bg-sheet-card px-4 py-3 text-left text-[14.5px] text-sheet-ink shadow-card transition-all hover:-translate-y-px hover:border-signal-edge hover:shadow-lift"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
