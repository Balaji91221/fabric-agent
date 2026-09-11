"""Talks to a Microsoft Fabric semantic model over the Power BI REST API.

Live path:
    POST {api_base}/datasets/{datasetId}/executeQueries
    POST {api_base}/groups/{workspaceId}/datasets/{datasetId}/executeQueries

Schema discovery uses the DAX INFO functions (INFO.TABLES / INFO.COLUMNS /
INFO.MEASURES / INFO.RELATIONSHIPS), which are reachable through the same
endpoint — no XMLA connection required.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

from .config import Settings
from . import demo_model


class DaxRejected(Exception):
    """Raised when a query isn't a safe read-only DAX statement."""


class FabricError(Exception):
    """Raised when Fabric returns an error we should show the agent."""


_ALLOWED_START = re.compile(r"^\s*(DEFINE|EVALUATE)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(ALTER|CREATE|DROP|INSERT|UPDATE|DELETE|REFRESH|BACKUP|RESTORE|EXEC(UTE)?)\b",
    re.IGNORECASE,
)


def guard_dax(dax: str) -> str:
    """Allow read-only DAX only. Fabric will also refuse writes, but failing
    here keeps a bad query from ever leaving the process."""
    query = (dax or "").strip().rstrip(";")
    if not query:
        raise DaxRejected("The query was empty. Send a DAX statement starting with EVALUATE.")
    if not _ALLOWED_START.match(query):
        raise DaxRejected(
            "Only read-only DAX is allowed. Start the query with EVALUATE (or DEFINE ... EVALUATE)."
        )
    if _FORBIDDEN.search(query):
        raise DaxRejected("Write and admin statements are blocked on this endpoint.")
    return query


class FabricClient:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._schema_cache: dict[str, Any] | None = None
        self._http = httpx.AsyncClient(timeout=60.0)

    @property
    def live(self) -> bool:
        return self.s.fabric_configured

    async def aclose(self) -> None:
        await self._http.aclose()

    # -- auth ----------------------------------------------------------- #

    async def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        url = f"https://login.microsoftonline.com/{self.s.tenant_id}/oauth2/v2.0/token"
        resp = await self._http.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.s.client_id,
                "client_secret": self.s.client_secret,
                "scope": self.s.aad_scope,
            },
        )
        if resp.status_code != 200:
            raise FabricError(f"Entra ID token request failed ({resp.status_code}): {resp.text[:400]}")
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + float(payload.get("expires_in", 3600))
        return self._token

    def _query_url(self) -> str:
        base = self.s.powerbi_api_base.rstrip("/")
        if self.s.workspace_id:
            return f"{base}/groups/{self.s.workspace_id}/datasets/{self.s.dataset_id}/executeQueries"
        return f"{base}/datasets/{self.s.dataset_id}/executeQueries"

    # -- queries -------------------------------------------------------- #

    async def run_dax(self, dax: str, max_rows: int | None = None) -> dict[str, Any]:
        """Execute DAX and return {columns, rows, rowCount, truncated}."""
        query = guard_dax(dax)
        limit = max_rows or self.s.max_rows_returned

        if not self.live:
            result = demo_model.execute_dax(query)
        else:
            token = await self._access_token()
            resp = await self._http.post(
                self._query_url(),
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "queries": [{"query": query}],
                    "serializerSettings": {"includeNulls": True},
                },
            )
            if resp.status_code >= 400:
                raise FabricError(_readable_error(resp))
            tables = resp.json().get("results", [{}])[0].get("tables", [{}])
            raw_rows = tables[0].get("rows", []) if tables else []
            result = {
                "columns": list(raw_rows[0].keys()) if raw_rows else [],
                "rows": raw_rows,
                "rowCount": len(raw_rows),
            }

        rows = result["rows"]
        truncated = len(rows) > limit
        return {
            "columns": [_strip_brackets(c) for c in result["columns"]],
            "rows": [{_strip_brackets(k): v for k, v in r.items()} for r in rows[:limit]],
            "rowCount": len(rows),
            "truncated": truncated,
            "dax": query,
        }

    # -- schema --------------------------------------------------------- #

    async def get_schema(self, refresh: bool = False) -> dict[str, Any]:
        if self._schema_cache is not None and not refresh:
            return self._schema_cache

        if not self.live:
            self._schema_cache = {**demo_model.SCHEMA, "source": "demo"}
            return self._schema_cache

        tables = await self._info("EVALUATE INFO.TABLES()")
        columns = await self._info("EVALUATE INFO.COLUMNS()")
        measures = await self._info("EVALUATE INFO.MEASURES()")
        relationships = await self._info("EVALUATE INFO.RELATIONSHIPS()")

        table_by_id = {t.get("ID"): t.get("Name") for t in tables}
        grouped: dict[str, list[dict[str, str]]] = {}
        for c in columns:
            tname = table_by_id.get(c.get("TableID"))
            if not tname or c.get("Type") == 3:  # skip row-number columns
                continue
            grouped.setdefault(tname, []).append(
                {"name": c.get("ExplicitName") or c.get("InferredName") or "", "dataType": str(c.get("ExplicitDataType"))}
            )

        self._schema_cache = {
            "name": self.s.dataset_id,
            "source": "fabric",
            "tables": [
                {"name": t.get("Name"), "description": t.get("Description") or "", "columns": grouped.get(t.get("Name"), [])}
                for t in tables
                if not t.get("IsHidden")
            ],
            "measures": [
                {
                    "name": m.get("Name"),
                    "table": table_by_id.get(m.get("TableID"), ""),
                    "expression": (m.get("Expression") or "").strip(),
                    "formatString": m.get("FormatString") or "",
                }
                for m in measures
                if not m.get("IsHidden")
            ],
            "relationships": [
                {
                    "from": f"{table_by_id.get(r.get('FromTableID'), '?')}",
                    "to": f"{table_by_id.get(r.get('ToTableID'), '?')}",
                    "cardinality": "many-to-one",
                }
                for r in relationships
            ],
        }
        return self._schema_cache

    async def _info(self, dax: str) -> list[dict[str, Any]]:
        try:
            result = await self.run_dax(dax, max_rows=5000)
        except FabricError:
            return []
        return [{_strip_brackets(k): v for k, v in row.items()} for row in result["rows"]]


def _strip_brackets(name: str) -> str:
    """`Sales[Total Sales]` and `[Total Sales]` both become `Total Sales`."""
    if not isinstance(name, str):
        return str(name)
    match = re.search(r"\[([^\]]+)\]\s*$", name)
    return match.group(1) if match else name


def _readable_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        detail = body.get("error", {}).get("pbi.error", {}).get("details", [])
        if detail:
            return str(detail[0].get("detail", {}).get("value", body))
        return str(body.get("error", body))[:600]
    except Exception:
        return f"HTTP {resp.status_code}: {resp.text[:400]}"


def schema_prompt(schema: dict[str, Any]) -> str:
    """Compact text version of the model, for the system prompt."""
    lines = [f"Semantic model: {schema.get('name')}", "", "Tables and columns:"]
    for t in schema.get("tables", []):
        cols = ", ".join(c["name"] for c in t.get("columns", []))
        note = f"  -- {t['description']}" if t.get("description") else ""
        lines.append(f"  '{t['name']}'[{cols}]{note}")
    lines.append("")
    lines.append("Measures (always prefer these over re-deriving arithmetic):")
    for m in schema.get("measures", []):
        lines.append(f"  [{m['name']}] = {m['expression']}")
    if schema.get("relationships"):
        lines.append("")
        lines.append("Relationships:")
        for r in schema["relationships"]:
            lines.append(f"  {r['from']} -> {r['to']} ({r.get('cardinality', '')})")
    return "\n".join(lines)
