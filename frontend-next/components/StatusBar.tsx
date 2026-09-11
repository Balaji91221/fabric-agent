"use client";

import type { AgentInfo } from "@/lib/types";

interface Props {
  info: AgentInfo | null;
  error?: string | null;
  onReset: () => void;
  canReset: boolean;
}

export default function StatusBar({ info, error, onReset, canReset }: Props) {
  const live = info?.mode === "live";

  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-shell-line bg-shell px-5 py-2.5 md:px-8">
      <div className="flex items-center gap-2">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            error ? "bg-flag" : live ? "bg-signal-edge" : "bg-flag"
          }`}
          aria-hidden
        />
        <span className="text-meta font-medium text-white">
          {error
            ? "Backend unreachable"
            : live
              ? "Connected to Fabric"
              : info
                ? "Demo model"
                : "Connecting"}
        </span>
      </div>

      {info && !error && (
        <>
          <Field label="Agent" value={info.id} mono />
          <Field label="Reasoning" value={info.reasoning_model} />
          {live && <Field label="Dataset" value={info.dataset_id} mono truncate />}
        </>
      )}

      <button
        type="button"
        onClick={onReset}
        disabled={!canReset}
        className="ml-auto rounded-chip border border-shell-line px-2.5 py-1 text-micro text-shell-text transition-colors hover:border-signal hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
      >
        Clear session
      </button>
    </header>
  );
}

function Field({
  label,
  value,
  mono,
  truncate,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-micro text-shell-dim">{label}</span>
      <span
        className={`text-meta text-shell-text ${mono ? "font-mono text-micro" : ""} ${
          truncate ? "max-w-[16ch] truncate" : ""
        }`}
      >
        {value}
      </span>
    </div>
  );
}
