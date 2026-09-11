const CURRENCY = /sales|cost|margin|amount|revenue|price|value/i;

/** Formats a cell using the column name as the only available hint. */
export function formatValue(column: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  if (column.includes("%")) return `${(value * 100).toFixed(1)}%`;
  if (CURRENCY.test(column)) {
    return value.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    });
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function isNumericColumn(column: string, rows: Record<string, unknown>[]): boolean {
  return rows.some((r) => typeof r[column] === "number");
}

export function columnExtent(column: string, rows: Record<string, unknown>[]): number {
  return rows.reduce((max, r) => {
    const v = r[column];
    return typeof v === "number" ? Math.max(max, Math.abs(v)) : max;
  }, 0);
}

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/* ------------------------------------------------------------------ */
/* DAX tokenizer — small on purpose, only what the agent actually emits */
/* ------------------------------------------------------------------ */

const KEYWORDS = new Set(
  `EVALUATE DEFINE MEASURE VAR RETURN ORDER BY ASC DESC START AT`.split(" "),
);

const FUNCTIONS = new Set(
  `SUMMARIZECOLUMNS CALCULATE CALCULATETABLE FILTER ALL ALLSELECTED ALLEXCEPT VALUES
   DISTINCT TOPN ROW ADDCOLUMNS SELECTCOLUMNS TREATAS KEEPFILTERS DIVIDE SUM SUMX
   COUNTROWS COUNT COUNTX AVERAGE AVERAGEX MAX MAXX MIN MINX RELATED RELATEDTABLE
   SAMEPERIODLASTYEAR DATEADD DATESYTD DATESBETWEEN TOTALYTD RANKX EARLIER
   IF SWITCH ISBLANK BLANK NOT AND OR CONCATENATE FORMAT`
    .split(/\s+/)
    .filter(Boolean),
);

export type Token = { text: string; type: "kw" | "fn" | "str" | "num" | "col" | "plain" };

export function tokenizeDax(dax: string): Token[] {
  const tokens: Token[] = [];
  // Strings, bracketed identifiers, words, numbers, everything else.
  const pattern = /("[^"]*")|(\[[^\]]*\])|('[^']*')|([A-Za-z_][A-Za-z0-9_]*)|(\d+(?:\.\d+)?)|([\s\S])/g;

  let match: RegExpExecArray | null;
  while ((match = pattern.exec(dax)) !== null) {
    const [text, str, bracket, quoted, word, num] = match;
    if (str) tokens.push({ text, type: "str" });
    else if (bracket) tokens.push({ text, type: "col" });
    else if (quoted) tokens.push({ text, type: "col" });
    else if (word) {
      const upper = word.toUpperCase();
      if (KEYWORDS.has(upper)) tokens.push({ text, type: "kw" });
      else if (FUNCTIONS.has(upper)) tokens.push({ text, type: "fn" });
      else tokens.push({ text, type: "plain" });
    } else if (num) tokens.push({ text, type: "num" });
    else tokens.push({ text, type: "plain" });
  }

  // `ORDER BY` reads as one keyword; merge the whitespace between them.
  return tokens;
}

/* ------------------------------------------------------------------ */
/* Minimal markdown — bold, italic, inline code, bullets              */
/* ------------------------------------------------------------------ */

export type MdNode = { kind: "p" | "li"; html: string };

export function parseMarkdown(md: string): MdNode[] {
  const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (s: string) =>
    escape(s)
      .replace(/\*\*(.+?)\*\*/g, '<strong class="font-medium text-signal-deep">$1</strong>')
      .replace(/(^|\s)\*(?!\s)(.+?)\*/g, '$1<em>$2</em>')
      .replace(/`(.+?)`/g, '<code class="font-mono text-[.88em] bg-signal-wash px-1 py-px rounded-chip">$1</code>');

  const nodes: MdNode[] = [];
  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) continue;
    if (/^\s*[-*]\s+/.test(line)) nodes.push({ kind: "li", html: inline(line.replace(/^\s*[-*]\s+/, "")) });
    else nodes.push({ kind: "p", html: inline(line) });
  }
  return nodes;
}
