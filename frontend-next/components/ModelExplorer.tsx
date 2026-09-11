"use client";

import { useMemo, useState } from "react";
import type { ModelSchema } from "@/lib/types";
import { ChevronIcon, LinkIcon, SearchIcon, SigmaIcon, TableIcon } from "./Icons";

interface Props {
  schema: ModelSchema | null;
  error?: string | null;
  onAsk: (question: string) => void;
}

export default function ModelExplorer({ schema, error, onAsk }: Props) {
  const [filter, setFilter] = useState("");
  const [openTables, setOpenTables] = useState<Record<string, boolean>>({});
  const [openMeasures, setOpenMeasures] = useState<Record<string, boolean>>({});

  const q = filter.trim().toLowerCase();

  const tables = useMemo(() => {
    if (!schema) return [];
    if (!q) return schema.tables;
    return schema.tables.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.columns.some((c) => c.name.toLowerCase().includes(q)),
    );
  }, [schema, q]);

  const measures = useMemo(() => {
    if (!schema) return [];
    if (!q) return schema.measures;
    return schema.measures.filter(
      (m) => m.name.toLowerCase().includes(q) || m.expression.toLowerCase().includes(q),
    );
  }, [schema, q]);

  return (
    <aside className="flex h-full min-h-0 w-full flex-col bg-shell text-shell-text">
      <header className="border-b border-shell-line px-5 pb-4 pt-5">
        <p className="text-micro text-shell-dim">Semantic model</p>
        <h1 className="mt-1 font-read text-[22px] leading-tight text-white">
          {schema?.name ?? (error ? "Unavailable" : "Loading…")}
        </h1>
        {schema && (
          <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-micro text-shell-dim">
            <span>{schema.tables.length} tables</span>
            <span className="text-shell-line">·</span>
            <span>{schema.measures.length} measures</span>
            <span className="text-shell-line">·</span>
            <span className="text-signal-edge">read-only</span>
          </p>
        )}
      </header>

      {schema && (
        <div className="border-b border-shell-line px-4 py-3">
          <div className="flex items-center gap-2 rounded-chip bg-shell-raised px-2.5 py-1.5 ring-1 ring-inset ring-shell-line focus-within:ring-signal">
            <SearchIcon className="text-shell-dim" />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter tables, columns, measures"
              aria-label="Filter the model"
              className="w-full bg-transparent text-meta text-white placeholder:text-shell-dim focus:outline-none"
            />
          </div>
        </div>
      )}

      <div className="scroll-shell min-h-0 flex-1 overflow-y-auto pb-8">
        {error && (
          <p className="px-5 py-6 text-meta leading-relaxed text-shell-dim">
            The model could not be read. Check that the agent backend is running, then reload.
          </p>
        )}

        {schema && (
          <>
            <SectionHeading icon={<TableIcon />} label="Tables" count={tables.length} />
            <ul>
              {tables.map((t) => {
                const open = openTables[t.name] ?? false;
                return (
                  <li key={t.name}>
                    <button
                      type="button"
                      onClick={() => setOpenTables((s) => ({ ...s, [t.name]: !open }))}
                      aria-expanded={open}
                      className="group flex w-full items-center gap-2 border-l-2 border-transparent py-1.5 pl-4 pr-4 text-left hover:border-signal hover:bg-shell-hover"
                    >
                      <ChevronIcon
                        className={`text-shell-dim transition-transform ${open ? "rotate-90" : ""}`}
                      />
                      <span className="text-[13.5px] text-white">{t.name}</span>
                      <span className="ml-auto tnum text-micro text-shell-dim">
                        {t.columns.length}
                      </span>
                    </button>

                    {open && (
                      <div className="animate-rise pb-2 pl-9 pr-4">
                        {t.description && (
                          <p className="pb-1.5 pt-0.5 text-micro leading-snug text-shell-dim">
                            {t.description}
                          </p>
                        )}
                        <ul className="space-y-px">
                          {t.columns.map((c) => (
                            <li
                              key={c.name}
                              className="flex items-baseline justify-between gap-3 py-0.5"
                            >
                              <span className="font-mono text-micro text-shell-text">{c.name}</span>
                              {c.dataType && (
                                <span className="shrink-0 text-[10.5px] text-shell-dim">
                                  {c.dataType}
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                        <button
                          type="button"
                          onClick={() => onAsk(`What can I learn from the ${t.name} table?`)}
                          className="mt-2 text-micro text-signal-edge hover:text-white"
                        >
                          Ask about {t.name}
                        </button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>

            <SectionHeading icon={<SigmaIcon />} label="Measures" count={measures.length} />
            <ul>
              {measures.map((m) => {
                const open = openMeasures[m.name] ?? false;
                return (
                  <li key={m.name}>
                    <button
                      type="button"
                      onClick={() => setOpenMeasures((s) => ({ ...s, [m.name]: !open }))}
                      aria-expanded={open}
                      className="flex w-full items-center gap-2 border-l-2 border-transparent py-1.5 pl-4 pr-4 text-left hover:border-signal hover:bg-shell-hover"
                    >
                      <ChevronIcon
                        className={`text-shell-dim transition-transform ${open ? "rotate-90" : ""}`}
                      />
                      <span className="text-[13.5px] text-signal-edge">{m.name}</span>
                    </button>
                    {open && (
                      <pre className="animate-rise mb-1.5 ml-9 mr-4 overflow-x-auto whitespace-pre-wrap break-words rounded-chip bg-shell-raised px-2.5 py-2 font-mono text-micro leading-relaxed text-shell-text">
                        {m.expression}
                      </pre>
                    )}
                  </li>
                );
              })}
            </ul>

            {schema.relationships && schema.relationships.length > 0 && (
              <>
                <SectionHeading
                  icon={<LinkIcon />}
                  label="Relationships"
                  count={schema.relationships.length}
                />
                <ul className="space-y-1 px-4 pt-1">
                  {schema.relationships.map((r, i) => (
                    <li key={i} className="font-mono text-micro leading-relaxed text-shell-dim">
                      {r.from}
                      <span className="px-1 text-shell-line">to</span>
                      {r.to}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </aside>
  );
}

function SectionHeading({
  icon,
  label,
  count,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
}) {
  return (
    <h2 className="flex items-center gap-2 px-4 pb-1.5 pt-5 text-meta font-medium text-shell-dim">
      <span className="text-shell-line">{icon}</span>
      {label}
      <span className="tnum ml-auto text-micro font-normal text-shell-line">{count}</span>
    </h2>
  );
}
