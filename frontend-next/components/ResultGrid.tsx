"use client";

import { useMemo } from "react";
import { columnExtent, formatValue, isNumericColumn } from "@/lib/format";
import type { AgentStep } from "@/lib/types";

interface Props {
  step: AgentStep;
}

/**
 * The grid does one thing beyond displaying values: it draws a magnitude bar
 * behind the *last* numeric column, so the shape of the result is readable
 * before any of the numbers are.
 */
export default function ResultGrid({ step }: Props) {
  const rows = step.rows ?? [];
  const columns = step.columns ?? [];

  const numeric = useMemo(
    () => new Set(columns.filter((c) => isNumericColumn(c, rows))),
    [columns, rows],
  );
  const barColumn = useMemo(() => {
    const nums = columns.filter((c) => numeric.has(c));
    return nums.length ? nums[nums.length - 1] : null;
  }, [columns, numeric]);
  const extent = barColumn ? columnExtent(barColumn, rows) : 0;

  if (!rows.length) {
    return (
      <p className="rounded-card border border-dashed border-sheet-line bg-sheet-card px-4 py-6 text-center text-meta text-sheet-muted">
        The query ran but matched no rows. Try widening the filters.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-card border border-sheet-line bg-sheet-card shadow-card">
      <div className="scroll-sheet max-h-[400px] overflow-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c}
                  scope="col"
                  className={`sticky top-0 z-10 whitespace-nowrap border-b border-sheet-line bg-sheet-card px-3.5 py-2.5 text-meta font-medium text-sheet-muted ${
                    numeric.has(c) ? "text-right" : "text-left"
                  }`}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="group transition-colors hover:bg-signal-wash/60">
                {columns.map((c) => {
                  const value = row[c];
                  const isNum = numeric.has(c);
                  const share =
                    barColumn === c && extent > 0 && typeof value === "number"
                      ? Math.abs(value) / extent
                      : 0;

                  return (
                    <td
                      key={c}
                      className={`relative whitespace-nowrap border-b border-sheet-line/70 px-3.5 py-2 ${
                        isNum ? "tnum pb-3 text-right font-mono" : "text-left"
                      } ${barColumn === c ? "text-sheet-ink" : "text-sheet-ink"}`}
                    >
                      {share > 0 && (
                        <span
                          aria-hidden
                          style={{ width: `${Math.max(share * 100, 3)}%` }}
                          className="animate-grow absolute bottom-[3px] right-[14px] h-[3px] origin-right rounded-full bg-signal/40"
                        />
                      )}
                      <span className="relative">{formatValue(c, value)}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-sheet-line bg-[#FBFCFC] px-3.5 py-2 text-micro text-sheet-muted">
        <span className="tnum">
          {rows.length} {rows.length === 1 ? "row" : "rows"}
          {step.truncated && step.rowCount ? ` of ${step.rowCount}` : ""}
        </span>
        <span className="tnum">
          {columns.length} {columns.length === 1 ? "column" : "columns"}
        </span>
        {step.truncated && (
          <span className="text-flag">
            Result capped — narrow the question for the full set.
          </span>
        )}
      </div>
    </div>
  );
}
