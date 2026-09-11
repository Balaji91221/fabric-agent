"""A small in-memory stand-in for a Fabric semantic model.

Used when no Fabric credentials are present so the whole stack runs offline.
The shape of everything here mirrors what the real `executeQueries` endpoint
returns, so swapping in live Fabric changes nothing above this layer.
"""

from __future__ import annotations

import random
import re
from datetime import date, timedelta
from typing import Any

MODEL_NAME = "Contoso Sales (demo)"

SCHEMA: dict[str, Any] = {
    "name": MODEL_NAME,
    "tables": [
        {
            "name": "Sales",
            "description": "One row per order line.",
            "columns": [
                {"name": "OrderDate", "dataType": "dateTime"},
                {"name": "ProductKey", "dataType": "int64"},
                {"name": "StoreKey", "dataType": "int64"},
                {"name": "Quantity", "dataType": "int64"},
                {"name": "NetAmount", "dataType": "decimal"},
                {"name": "Cost", "dataType": "decimal"},
            ],
        },
        {
            "name": "Product",
            "description": "Product dimension.",
            "columns": [
                {"name": "ProductKey", "dataType": "int64"},
                {"name": "Product", "dataType": "string"},
                {"name": "Category", "dataType": "string"},
                {"name": "Brand", "dataType": "string"},
            ],
        },
        {
            "name": "Store",
            "description": "Store dimension.",
            "columns": [
                {"name": "StoreKey", "dataType": "int64"},
                {"name": "Store", "dataType": "string"},
                {"name": "Country", "dataType": "string"},
                {"name": "Channel", "dataType": "string"},
            ],
        },
        {
            "name": "Date",
            "description": "Marked as the model date table.",
            "columns": [
                {"name": "Date", "dataType": "dateTime"},
                {"name": "Year", "dataType": "int64"},
                {"name": "Quarter", "dataType": "string"},
                {"name": "Month", "dataType": "string"},
                {"name": "MonthNumber", "dataType": "int64"},
            ],
        },
    ],
    "measures": [
        {"name": "Total Sales", "table": "Sales", "expression": "SUM ( Sales[NetAmount] )", "formatString": "\\$#,0"},
        {"name": "Total Cost", "table": "Sales", "expression": "SUM ( Sales[Cost] )", "formatString": "\\$#,0"},
        {"name": "Margin", "table": "Sales", "expression": "[Total Sales] - [Total Cost]", "formatString": "\\$#,0"},
        {"name": "Margin %", "table": "Sales", "expression": "DIVIDE ( [Margin], [Total Sales] )", "formatString": "0.0%"},
        {"name": "Units Sold", "table": "Sales", "expression": "SUM ( Sales[Quantity] )", "formatString": "#,0"},
        {"name": "Order Count", "table": "Sales", "expression": "COUNTROWS ( Sales )", "formatString": "#,0"},
        {"name": "Sales LY", "table": "Sales", "expression": "CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", "formatString": "\\$#,0"},
        {"name": "Sales YoY %", "table": "Sales", "expression": "DIVIDE ( [Total Sales] - [Sales LY], [Sales LY] )", "formatString": "0.0%"},
    ],
    "relationships": [
        {"from": "Sales[ProductKey]", "to": "Product[ProductKey]", "cardinality": "many-to-one"},
        {"from": "Sales[StoreKey]", "to": "Store[StoreKey]", "cardinality": "many-to-one"},
        {"from": "Sales[OrderDate]", "to": "Date[Date]", "cardinality": "many-to-one"},
    ],
}

CATEGORIES = ["Audio", "Computers", "Cameras", "Home Appliances", "Wearables"]
BRANDS = ["Northwind", "Adventure Works", "Litware", "Proseware"]
COUNTRIES = ["United States", "Germany", "India", "Japan", "United Kingdom"]
CHANNELS = ["Online", "Retail", "Reseller"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _build_facts() -> list[dict[str, Any]]:
    rng = random.Random(20240917)
    rows: list[dict[str, Any]] = []
    start = date(2023, 1, 1)
    for day_offset in range(0, 730, 1):
        d = start + timedelta(days=day_offset)
        for _ in range(rng.randint(2, 5)):
            category = rng.choice(CATEGORIES)
            base = {
                "Audio": 190, "Computers": 1150, "Cameras": 720,
                "Home Appliances": 430, "Wearables": 260,
            }[category]
            qty = rng.randint(1, 6)
            unit = base * rng.uniform(0.82, 1.25)
            # gentle year-over-year growth so YoY questions are interesting
            growth = 1.0 + (0.11 if d.year == 2024 else 0.0)
            net = round(unit * qty * growth, 2)
            rows.append({
                "OrderDate": d,
                "Year": d.year,
                "Quarter": f"Q{(d.month - 1) // 3 + 1}",
                "Month": MONTHS[d.month - 1],
                "MonthNumber": d.month,
                "Category": category,
                "Brand": rng.choice(BRANDS),
                "Country": rng.choice(COUNTRIES),
                "Channel": rng.choice(CHANNELS),
                "Quantity": qty,
                "NetAmount": net,
                "Cost": round(net * rng.uniform(0.55, 0.78), 2),
            })
    return rows


FACTS = _build_facts()

MEASURE_FNS = {
    "Total Sales": lambda rs: sum(r["NetAmount"] for r in rs),
    "Total Cost": lambda rs: sum(r["Cost"] for r in rs),
    "Units Sold": lambda rs: sum(r["Quantity"] for r in rs),
    "Order Count": lambda rs: len(rs),
    "Margin": lambda rs: sum(r["NetAmount"] for r in rs) - sum(r["Cost"] for r in rs),
}

GROUPABLE = {
    "Category": "Category", "Brand": "Brand", "Country": "Country",
    "Channel": "Channel", "Year": "Year", "Quarter": "Quarter",
    "Month": "Month", "Product": "Category", "Store": "Country",
}


def _measure_value(name: str, rows: list[dict[str, Any]]) -> float:
    if name in MEASURE_FNS:
        return round(MEASURE_FNS[name](rows), 2)
    if name == "Margin %":
        sales = MEASURE_FNS["Total Sales"](rows)
        margin = MEASURE_FNS["Margin"](rows)
        return round(margin / sales, 4) if sales else 0.0
    if name in ("Sales LY", "Sales YoY %"):
        by_year: dict[int, float] = {}
        for r in rows:
            by_year[r["Year"]] = by_year.get(r["Year"], 0.0) + r["NetAmount"]
        years = sorted(by_year)
        if len(years) < 2:
            return 0.0
        cur, prev = by_year[years[-1]], by_year[years[-2]]
        if name == "Sales LY":
            return round(prev, 2)
        return round((cur - prev) / prev, 4) if prev else 0.0
    return 0.0


def execute_dax(dax: str) -> dict[str, Any]:
    """Interpret a useful subset of DAX against the in-memory facts.

    This is intentionally shallow: it recognises SUMMARIZECOLUMNS-style
    group-by + measure queries, TOPN, and simple year filters. Anything it
    can't parse still returns a well-formed result so the agent can react.
    """
    text = " ".join(dax.split())

    measures = [m["name"] for m in SCHEMA["measures"] if f'"{m["name"]}"' in text or f"[{m['name']}]" in text]
    if not measures:
        measures = ["Total Sales"]

    # Filter clauses (TREATAS, and `Col = value`) are not group-by columns, so
    # strip them out before working out what the query groups on.
    groupable_text = re.sub(r"TREATAS\s*\(.*?\)\s*,", " ", text, flags=re.IGNORECASE | re.DOTALL)
    groupable_text = re.sub(r"\[[\w ]+\]\s*=\s*[^,)]+", " ", groupable_text)

    groups: list[str] = []
    for _table, col in re.findall(r"'?(\w[\w ]*?)'?\[(\w[\w ]*?)\]", groupable_text):
        if col in GROUPABLE and col not in groups and col not in measures:
            groups.append(col)

    rows = FACTS
    # An explicit year filter always applies, even when the query also groups
    # by year — that is what SUMMARIZECOLUMNS + TREATAS means.
    year_filter = re.search(r"TREATAS\s*\(\s*\{\s*(20\d\d)", text, re.IGNORECASE) or re.search(
        r"\[Year\]\s*=\s*(20\d\d)", text, re.IGNORECASE
    )
    if year_filter:
        rows = [r for r in rows if r["Year"] == int(year_filter.group(1))]
    else:
        loose_year = re.search(r"\b(20\d\d)\b", text)
        if loose_year and "Year" not in groups:
            rows = [r for r in rows if r["Year"] == int(loose_year.group(1))]

    for name, patt in (("Online", "Online"), ("Retail", "Retail"), ("Reseller", "Reseller")):
        if f'"{patt}"' in text:
            rows = [r for r in rows if r["Channel"] == name]

    if not groups:
        record = {m: _measure_value(m, rows) for m in measures}
        return {"columns": measures, "rows": [record], "rowCount": 1}

    buckets: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        key = tuple(r[GROUPABLE[g]] for g in groups)
        buckets.setdefault(key, []).append(r)

    out = []
    for key, group_rows in buckets.items():
        record = {g: key[i] for i, g in enumerate(groups)}
        for m in measures:
            record[m] = _measure_value(m, group_rows)
        out.append(record)

    sort_key = measures[0]
    descending = "DESC" in text.upper() or "TOPN" in text.upper()
    if groups == ["Year"] or groups == ["MonthNumber"]:
        out.sort(key=lambda r: r[groups[0]])
    else:
        out.sort(key=lambda r: r.get(sort_key, 0), reverse=descending or True)

    topn = re.search(r"TOPN\s*\(\s*(\d+)", text, re.IGNORECASE)
    if topn:
        out = out[: int(topn.group(1))]

    return {"columns": groups + measures, "rows": out, "rowCount": len(out)}
