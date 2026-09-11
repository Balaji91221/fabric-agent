"""The agent: turns a chat message into DAX, runs it, explains the answer.

Two execution paths share one interface:

* `_run_with_llm`  — an OpenAI-compatible tool-calling loop. Works with
  OpenAI, Azure OpenAI, or any local server that speaks the same API.
* `_run_offline`   — a deterministic planner used when no upstream LLM key is
  set, so the demo still answers real questions end to end.

Both yield `AgentEvent` objects, so streaming and non-streaming responses come
from the same code.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from .config import Settings
from .fabric import DaxRejected, FabricClient, FabricError, schema_prompt

SYSTEM_PROMPT = """You are a data analyst agent with read-only access to one Microsoft Fabric semantic model.

How to work:
1. Call `get_model_schema` first if you are unsure which tables, columns or measures exist. Never guess names.
2. Write a single DAX query and run it with `run_dax_query`. Prefer existing measures over rewriting their logic.
3. Read the returned rows and answer in plain language. Quote the actual numbers.
4. If the query errors, read the message, fix the DAX, and retry. Do not retry the same query unchanged.

DAX rules:
- Every query starts with EVALUATE, optionally preceded by DEFINE.
- Use SUMMARIZECOLUMNS for grouped aggregation, and wrap measures in double quotes:
  EVALUATE SUMMARIZECOLUMNS ( Product[Category], "Total Sales", [Total Sales] )
- Use TOPN plus ORDER BY for "top N" questions, and keep result sets small.
- Never attempt to write, refresh, or alter the model. It is read-only.

Answering:
- Lead with the number or the finding, then one or two lines of context.
- Format currency and percentages readably.
- If the model cannot answer the question, say exactly what is missing rather than inventing a figure.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_model_schema",
            "description": "List the tables, columns, measures and relationships in the semantic model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Optional table name to inspect in detail.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_dax_query",
            "description": "Run a read-only DAX query against the semantic model and return the rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dax": {
                        "type": "string",
                        "description": "A DAX statement beginning with EVALUATE or DEFINE.",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "One line on what this query is meant to answer.",
                    },
                },
                "required": ["dax"],
            },
        },
    },
]


@dataclass
class AgentEvent:
    kind: str  # "step" | "text" | "done" | "error"
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class Agent:
    def __init__(self, settings: Settings, fabric: FabricClient) -> None:
        self.s = settings
        self.fabric = fabric
        self._http = httpx.AsyncClient(timeout=settings.llm_timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def run(self, messages: list[dict[str, Any]]) -> AsyncIterator[AgentEvent]:
        if self.s.llm_configured:
            async for ev in self._run_with_llm(messages):
                yield ev
        else:
            async for ev in self._run_offline(messages):
                yield ev

    # ---------------------------------------------------------------- #
    # Tool execution
    # ---------------------------------------------------------------- #

    async def _call_tool(self, name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if name == "get_model_schema":
            schema = await self.fabric.get_schema()
            table = args.get("table")
            if table:
                match = next(
                    (t for t in schema["tables"] if t["name"].lower() == table.lower()), None
                )
                if not match:
                    names = ", ".join(t["name"] for t in schema["tables"])
                    return f"No table named '{table}'. Available tables: {names}", {}
                return json.dumps(match, default=str), {"tool": "schema", "table": table}
            return schema_prompt(schema), {"tool": "schema"}

        if name == "run_dax_query":
            dax = args.get("dax", "")
            try:
                result = await self.fabric.run_dax(dax)
            except DaxRejected as exc:
                return f"Query rejected: {exc}", {"tool": "dax", "dax": dax, "error": str(exc)}
            except FabricError as exc:
                return f"Fabric returned an error: {exc}", {"tool": "dax", "dax": dax, "error": str(exc)}
            payload = {
                "tool": "dax",
                "dax": result["dax"],
                "columns": result["columns"],
                "rows": result["rows"],
                "rowCount": result["rowCount"],
                "truncated": result["truncated"],
                "purpose": args.get("purpose", ""),
            }
            summary = json.dumps(
                {"columns": result["columns"], "rows": result["rows"], "rowCount": result["rowCount"]},
                default=str,
            )
            if result["truncated"]:
                summary += f"\n(Showing the first {len(result['rows'])} of {result['rowCount']} rows.)"
            return summary, payload

        return f"Unknown tool '{name}'.", {}

    # ---------------------------------------------------------------- #
    # LLM-driven loop
    # ---------------------------------------------------------------- #

    async def _run_with_llm(self, messages: list[dict[str, Any]]) -> AsyncIterator[AgentEvent]:
        schema = await self.fabric.get_schema()
        convo: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + schema_prompt(schema)}
        ]
        convo += [m for m in messages if m.get("role") != "system"]
        # keep any caller-supplied system message as extra guidance
        for m in messages:
            if m.get("role") == "system" and m.get("content"):
                convo[0]["content"] += "\n\nAdditional instructions from the client:\n" + str(m["content"])

        for _turn in range(self.s.max_tool_turns):
            reply = await self._chat(convo)
            calls = reply.get("tool_calls") or []

            if not calls:
                yield AgentEvent("text", reply.get("content") or "")
                yield AgentEvent("done")
                return

            convo.append(reply)
            for call in calls:
                fn = call["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                yield AgentEvent("step", f"{fn['name']}", data={"name": fn["name"], "args": args})
                content, payload = await self._call_tool(fn["name"], args)
                if payload:
                    yield AgentEvent("step", "result", data=payload)
                convo.append(
                    {"role": "tool", "tool_call_id": call["id"], "name": fn["name"], "content": content}
                )

        yield AgentEvent(
            "text",
            "I reached the tool-call limit for this question without settling on an answer. "
            "Try narrowing it to a single metric and grouping.",
        )
        yield AgentEvent("done")

    async def _chat(self, convo: list[dict[str, Any]]) -> dict[str, Any]:
        resp = await self._http.post(
            f"{self.s.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.s.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.s.llm_model,
                "messages": convo,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1,
            },
        )
        if resp.status_code >= 400:
            raise FabricError(f"Upstream model error ({resp.status_code}): {resp.text[:400]}")
        return resp.json()["choices"][0]["message"]

    # ---------------------------------------------------------------- #
    # Offline planner — keeps the demo honest without an LLM key
    # ---------------------------------------------------------------- #

    async def _run_offline(self, messages: list[dict[str, Any]]) -> AsyncIterator[AgentEvent]:
        question = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                question = str(m.get("content") or "")
                break

        schema = await self.fabric.get_schema()
        q = question.lower()

        if any(w in q for w in ("schema", "what tables", "what measures", "model structure", "columns")):
            yield AgentEvent("step", "get_model_schema", data={"name": "get_model_schema", "args": {}})
            yield AgentEvent("step", "result", data={"tool": "schema"})
            yield AgentEvent("text", _describe_schema(schema))
            yield AgentEvent("done")
            return

        dax, purpose = _plan_dax(q, schema)
        yield AgentEvent("step", "run_dax_query", data={"name": "run_dax_query", "args": {"dax": dax}})
        content, payload = await self._call_tool("run_dax_query", {"dax": dax, "purpose": purpose})
        if payload:
            yield AgentEvent("step", "result", data=payload)

        if payload.get("error"):
            yield AgentEvent("text", f"The query failed: {payload['error']}")
            yield AgentEvent("done")
            return

        yield AgentEvent("text", _narrate(payload, purpose))
        yield AgentEvent("done")


# -------------------------------------------------------------------- #
# Offline helpers
# -------------------------------------------------------------------- #

# Stems, so "country"/"countries" and "category"/"categories" both match.
_GROUP_HINTS = [
    ("categor", "Product[Category]", "Category"),
    ("brand", "Product[Brand]", "Brand"),
    ("countr", "Store[Country]", "Country"),
    ("region", "Store[Country]", "Country"),
    ("channel", "Store[Channel]", "Channel"),
    ("market", "Store[Country]", "Country"),
    ("store", "Store[Store]", "Store"),
    ("product", "Product[Product]", "Product"),
    ("month", "'Date'[Month]", "Month"),
    ("quarter", "'Date'[Quarter]", "Quarter"),
    ("year over year", "'Date'[Year]", "Year"),
    ("yoy", "'Date'[Year]", "Year"),
    ("year", "'Date'[Year]", "Year"),
]

_MEASURE_HINTS = [
    ("margin %", "Margin %"), ("margin percent", "Margin %"), ("margin", "Margin"),
    ("yoy", "Sales YoY %"), ("year over year", "Sales YoY %"), ("growth", "Sales YoY %"),
    ("last year", "Sales LY"),
    ("unit", "Units Sold"), ("quantity", "Units Sold"), ("volume", "Units Sold"),
    ("order", "Order Count"), ("transaction", "Order Count"),
    ("cost", "Total Cost"),
    ("revenue", "Total Sales"), ("sales", "Total Sales"), ("turnover", "Total Sales"),
]


def _plan_dax(q: str, schema: dict[str, Any]) -> tuple[str, str]:
    available = {m["name"] for m in schema.get("measures", [])}

    measure = "Total Sales"
    for token, name in _MEASURE_HINTS:
        if token in q and name in available:
            measure = name
            break

    group_col, group_label = None, None
    for token, col, label in _GROUP_HINTS:
        if token in q:
            group_col, group_label = col, label
            break

    year = None
    ym = re.search(r"\b(20\d\d)\b", q)
    if ym:
        year = ym.group(1)

    filter_clause = f", TREATAS ( {{ {year} }}, 'Date'[Year] )" if year else ""

    if not group_col:
        dax = f'EVALUATE\nROW ( "{measure}", [{measure}] )'
        if year:
            dax = (
                f'EVALUATE\nSUMMARIZECOLUMNS (\n    \'Date\'[Year],\n'
                f'    TREATAS ( {{ {year} }}, \'Date\'[Year] ),\n    "{measure}", [{measure}]\n)'
            )
        return dax, f"{measure}" + (f" for {year}" if year else " overall")

    topn = re.search(r"top\s+(\d+)", q)
    if topn or "top" in q or "best" in q or "worst" in q:
        n = int(topn.group(1)) if topn else 5
        ascending = "worst" in q or "lowest" in q or "bottom" in q
        order = "ASC" if ascending else "DESC"
        dax = (
            f"EVALUATE\nTOPN (\n    {n},\n    SUMMARIZECOLUMNS (\n"
            f"        {group_col}{filter_clause},\n"
            f'        "{measure}", [{measure}]\n    ),\n'
            f'    [{measure}], {order}\n)\nORDER BY [{measure}] {order}'
        )
        return dax, f"Top {n} {group_label} by {measure}"

    dax = (
        f"EVALUATE\nSUMMARIZECOLUMNS (\n    {group_col}{filter_clause},\n"
        f'    "{measure}", [{measure}]\n)\nORDER BY [{measure}] DESC'
    )
    return dax, f"{measure} by {group_label}" + (f" in {year}" if year else "")


def _fmt(name: str, value: Any) -> str:
    if not isinstance(value, (int, float)):
        return str(value)
    if "%" in name:
        return f"{value * 100:.1f}%"
    if any(w in name.lower() for w in ("sales", "cost", "margin", "amount", "revenue")):
        return f"${value:,.0f}"
    return f"{value:,.0f}"


def _describe_schema(schema: dict[str, Any]) -> str:
    lines = [f"**{schema.get('name')}** exposes {len(schema.get('tables', []))} tables and {len(schema.get('measures', []))} measures.", ""]
    for t in schema.get("tables", []):
        lines.append(f"- **{t['name']}** — {', '.join(c['name'] for c in t.get('columns', []))}")
    lines.append("")
    lines.append("Measures: " + ", ".join(f"[{m['name']}]" for m in schema.get("measures", [])))
    return "\n".join(lines)


def _narrate(payload: dict[str, Any], purpose: str) -> str:
    rows = payload.get("rows") or []
    cols = payload.get("columns") or []
    if not rows:
        return "That query came back empty. Nothing in the model matches those filters."

    numeric = [c for c in cols if isinstance(rows[0].get(c), (int, float))]
    measure = numeric[-1] if numeric else cols[-1]
    dim_cols = [c for c in cols if c != measure]

    if len(rows) == 1 and not dim_cols:
        return f"{measure} is **{_fmt(measure, rows[0][measure])}**."

    def label(row):
        return " / ".join(str(row[c]) for c in dim_cols) if dim_cols else measure

    head, tail = rows[0], rows[-1]
    values = [r[measure] for r in rows if isinstance(r.get(measure), (int, float))]
    total = sum(values)

    out = [
        f"**{label(head)}** leads on {measure} at **{_fmt(measure, head[measure])}**."
    ]

    if len(rows) > 1 and total and "%" not in measure:
        share = head[measure] / total * 100
        out[0] += f" That is {share:.0f}% of the {_fmt(measure, total)} across all {len(rows)} rows returned."

    if len(rows) > 2:
        spread = (head[measure] / tail[measure]) if tail[measure] else 0
        gap = (
            f"The gap to {label(tail)} at {_fmt(measure, tail[measure])} is "
            + (f"{spread:.1f}x" if spread > 1.15 else "small — these are close together")
            + "."
        )
        out.append(gap)

    return "\n\n".join(out)
