"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AnswerProse from "./AnswerProse";
import Composer from "./Composer";
import DaxBlock from "./DaxBlock";
import EmptyState from "./EmptyState";
import ModelExplorer from "./ModelExplorer";
import ResultGrid from "./ResultGrid";
import StatusBar from "./StatusBar";
import { WarnIcon } from "./Icons";
import { formatDuration } from "@/lib/format";
import { streamChat } from "@/lib/stream";
import type { AgentInfo, AgentStep, Block, ChatMessage, ModelSchema, Turn } from "@/lib/types";

interface Props {
  info: AgentInfo | null;
  schema: ModelSchema | null;
  bootError: string | null;
}

export default function Console({ info, schema, bootError }: Props) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [railOpen, setRailOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<ChatMessage[]>([]);
  const pinnedToBottom = useRef(true);

  // Only auto-scroll while the reader is already at the bottom, so scrolling
  // back to re-read a query doesn't get yanked away mid-stream.
  useEffect(() => {
    const el = scrollRef.current;
    if (el && pinnedToBottom.current) el.scrollTop = el.scrollHeight;
  });

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    pinnedToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || busy) return;

      setDraft("");
      setBusy(true);
      setRailOpen(false);
      pinnedToBottom.current = true;

      const id = `${Date.now()}`;
      const started = performance.now();
      let lastStep = started;

      setTurns((t) => [...t, { id, question: text, blocks: [], answer: "", status: "working" }]);

      const patch = (fn: (t: Turn) => Turn) =>
        setTurns((all) => all.map((t) => (t.id === id ? fn(t) : t)));

      historyRef.current = [...historyRef.current, { role: "user", content: text }];

      try {
        const answer = await streamChat(historyRef.current, {
          onStep: (step: AgentStep) => {
            const now = performance.now();
            const elapsed = now - lastStep;
            lastStep = now;

            patch((t) => {
              const blocks: Block[] = [...t.blocks];
              if (step.tool === "dax") {
                if (step.error) blocks.push({ kind: "error", text: step.error });
                else blocks.push({ kind: "query", step, elapsedMs: elapsed });
              } else if (step.name) {
                const label =
                  step.name === "run_dax_query" ? "Writing the query" : "Reading the model schema";
                if (!blocks.some((b) => b.kind === "note" && b.text === label)) {
                  blocks.push({ kind: "note", text: label });
                }
              }
              return { ...t, blocks };
            });
          },
          onDelta: (answerSoFar) => patch((t) => ({ ...t, answer: answerSoFar })),
        });

        historyRef.current = [...historyRef.current, { role: "assistant", content: answer }];
        patch((t) => ({
          ...t,
          status: "done",
          answer,
          elapsedMs: performance.now() - started,
        }));
      } catch (err) {
        const message = err instanceof Error ? err.message : "The request failed.";
        patch((t) => ({
          ...t,
          status: "failed",
          blocks: [...t.blocks, { kind: "error", text: message }],
        }));
      } finally {
        setBusy(false);
      }
    },
    [busy],
  );

  const reset = useCallback(() => {
    historyRef.current = [];
    setTurns([]);
    setDraft("");
  }, []);

  return (
    <div className="flex h-dvh flex-col bg-shell lg:grid lg:grid-cols-[304px_1fr] lg:grid-rows-1">
      {/* Rail — a drawer on small screens, a column on large ones */}
      <div
        className={`${
          railOpen ? "flex" : "hidden"
        } min-h-0 border-b border-shell-line lg:flex lg:border-b-0 lg:border-r`}
      >
        <ModelExplorer schema={schema} error={bootError} onAsk={ask} />
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <StatusBar info={info} error={bootError} onReset={reset} canReset={turns.length > 0} />

        <button
          type="button"
          onClick={() => setRailOpen((v) => !v)}
          className="border-b border-shell-line bg-shell px-5 py-2 text-left text-meta text-shell-text lg:hidden"
        >
          {railOpen ? "Hide" : "Show"} model explorer
        </button>

        <div
          ref={scrollRef}
          onScroll={onScroll}
          className="scroll-sheet min-h-0 flex-1 overflow-y-auto bg-sheet px-5 pb-10 pt-7 md:px-8"
        >
          {turns.length === 0 ? (
            <EmptyState schema={schema} onAsk={ask} />
          ) : (
            <div className="mx-auto flex max-w-[78ch] flex-col gap-10">
              {turns.map((turn) => (
                <TurnView key={turn.id} turn={turn} />
              ))}
            </div>
          )}
        </div>

        <div className="relative h-px bg-sheet-line" aria-hidden>
          {busy && (
            <span className="animate-sweep absolute inset-y-0 w-[40%] bg-signal" />
          )}
        </div>

        <Composer
          value={draft}
          onChange={setDraft}
          onSubmit={() => ask(draft)}
          busy={busy}
          disabled={Boolean(bootError)}
        />
      </div>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const working = turn.status === "working";

  return (
    <article className="animate-rise flex flex-col gap-4">
      <h2 className="border-l-2 border-sheet-ink pl-3.5 text-[17px] font-medium leading-snug text-sheet-ink">
        {turn.question}
      </h2>

      {turn.blocks.map((block, i) => {
        if (block.kind === "note") {
          return (
            <p key={i} className="flex items-center gap-2 text-meta text-sheet-muted">
              <span className="h-1 w-1 rounded-full bg-signal" aria-hidden />
              {block.text}
            </p>
          );
        }
        if (block.kind === "error") {
          return (
            <p
              key={i}
              className="flex items-start gap-2 rounded-card border border-flag/30 bg-flag/[0.06] px-3.5 py-2.5 text-[13.5px] leading-relaxed text-flag"
            >
              <WarnIcon className="mt-px" />
              <span>{block.text}</span>
            </p>
          );
        }
        return (
          <div key={i} className="flex flex-col gap-2.5">
            <DaxBlock dax={block.step.dax ?? ""} purpose={block.step.purpose} />
            <ResultGrid step={block.step} />
          </div>
        );
      })}

      {working && !turn.answer && turn.blocks.length === 0 && (
        <p className="animate-pulse2 text-meta text-sheet-muted">Planning the query…</p>
      )}

      <AnswerProse text={turn.answer} streaming={working} />

      {turn.status === "done" && turn.elapsedMs !== undefined && (
        <p className="tnum text-micro text-sheet-muted">
          Answered in {formatDuration(turn.elapsedMs)}
        </p>
      )}
    </article>
  );
}
