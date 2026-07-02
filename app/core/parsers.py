"""File format parsers for POS source data.

Supported inputs:
- CSV (ISO dates, dot decimal)
- CSV-DE (DD.MM.YYYY, comma decimal)
- JSON / JSON-lines (FR-style tracking logs)
- XLSX (Excel exports)
- TXT / EDI (pipe-delimited HDR/LIN/TRL)
"""
from __future__ import annotations

import io
import json
import re
from typing import List

import pandas as pd

# ---------------------------------------------------------------------------
# Canonical raw schema produced by every parser
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS = [
    "sale_date_raw",
    "store_id_raw",
    "sku_raw",
    "brand_raw",
    "category_raw",
    "units_raw",
    "gross_sales_raw",
    "net_sales_raw",
    "discount_raw",
    "promo_raw",
    "currency_raw",
    "channel_raw",
    "source_file",
    "source_format",
]


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_COLUMNS)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def parse_csv(content: bytes, filename: str) -> pd.DataFrame:
    """Parse a CSV file with tolerant settings (handles malformed rows)."""
    text = content.decode("utf-8", errors="replace")
    try:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python",
                         on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(io.StringIO(text), sep=",", engine="python",
                         on_bad_lines="skip")

    df.columns = [c.strip().lower() for c in df.columns]
    out = _empty_frame()
    out["sale_date_raw"] = df.get("sale_date")
    out["store_id_raw"] = df.get("store_id")
    out["sku_raw"] = df.get("sku")
    out["brand_raw"] = df.get("brand")
    out["category_raw"] = df.get("category")
    out["units_raw"] = df.get("units")
    out["net_sales_raw"] = df.get("net_sales")
    out["gross_sales_raw"] = df.get("gross_sales", df.get("net_sales"))
    out["discount_raw"] = df.get("discount_pct")
    out["promo_raw"] = df.get("promo")
    out["currency_raw"] = df.get("currency", "EUR")
    out["channel_raw"] = df.get("channel", "store")
    out["source_file"] = filename
    out["source_format"] = "csv"
    return out


# ---------------------------------------------------------------------------
# JSON / JSON-lines
# ---------------------------------------------------------------------------
def parse_json(content: bytes, filename: str) -> pd.DataFrame:
    text = content.decode("utf-8", errors="replace").strip()

    records: List[dict] = []
    # Try line-delimited JSON first
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Fallback: whole-file JSON array
    if not records:
        try:
            obj = json.loads(text)
            if isinstance(obj, list):
                records = obj
            elif isinstance(obj, dict):
                records = [obj]
        except json.JSONDecodeError:
            pass

    if not records:
        return _empty_frame()

    df = pd.DataFrame(records)
    out = _empty_frame()
    out["sale_date_raw"] = df.get("dt", df.get("date"))
    out["store_id_raw"] = df.get("shop", df.get("store_id"))
    out["sku_raw"] = df.get("sku")
    out["brand_raw"] = df.get("brand")
    out["category_raw"] = df.get("cat", df.get("category"))
    out["units_raw"] = df.get("qty", df.get("units"))
    out["gross_sales_raw"] = df.get("gross")
    out["net_sales_raw"] = df.get("net")
    out["discount_raw"] = df.get("disc", df.get("discount_pct"))
    out["promo_raw"] = df.get("promo")
    out["currency_raw"] = df.get("cur", df.get("currency", "EUR"))
    out["channel_raw"] = df.get("channel", "store")
    out["source_file"] = filename
    out["source_format"] = "json"
    return out


# ---------------------------------------------------------------------------
# XLSX
# ---------------------------------------------------------------------------
def parse_xlsx(content: bytes, filename: str) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content))
    df.columns = [str(c).strip().lower() for c in df.columns]

    out = _empty_frame()
    out["sale_date_raw"] = df.get("sale_date", df.get("date"))
    out["store_id_raw"] = df.get("store_id", df.get("shop"))
    out["sku_raw"] = df.get("sku")
    out["brand_raw"] = df.get("brand")
    out["category_raw"] = df.get("category")
    out["units_raw"] = df.get("units", df.get("qty"))
    out["net_sales_raw"] = df.get("net_sales", df.get("net"))
    out["gross_sales_raw"] = df.get("gross_sales", df.get("gross", df.get("net_sales")))
    out["discount_raw"] = df.get("discount_pct", df.get("disc"))
    out["promo_raw"] = df.get("promo")
    out["currency_raw"] = df.get("currency", "EUR")
    out["channel_raw"] = df.get("channel", "store")
    out["source_file"] = filename
    out["source_format"] = "xlsx"
    return out


# ---------------------------------------------------------------------------
# TXT / EDI (pipe-delimited)
# ---------------------------------------------------------------------------
_LIN_RE = re.compile(
    r"^LIN\|(?P<date>[^|]+)\|(?P<store>[^|]+)\|(?P<sku>[^|]+)\|"
    r"(?P<brand>[^|]+)\|(?P<category>[^|]+)\|"
    r"QTY=(?P<qty>-?[\d.,]+)\|NET=(?P<net>-?[\d.,]+)"
    r"(?:\|DISC=(?P<disc>-?[\d.,]+))?",
    re.IGNORECASE,
)


def parse_edi(content: bytes, filename: str) -> pd.DataFrame:
    text = content.decode("utf-8", errors="replace")
    currency = "EUR"
    rows: List[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("HDR|"):
            parts = line.split("|")
            if len(parts) >= 5:
                currency = parts[4] or "EUR"
            continue
        if line.startswith("TRL"):
            continue
        m = _LIN_RE.match(line)
        if not m:
            continue
        g = m.groupdict()
        rows.append({
            "sale_date_raw": g["date"],
            "store_id_raw": g["store"],
            "sku_raw": g["sku"],
            "brand_raw": g["brand"],
            "category_raw": g["category"],
            "units_raw": g["qty"],
            "net_sales_raw": g["net"],
            "gross_sales_raw": g["net"],
            "discount_raw": g.get("disc"),
            "promo_raw": None,
            "currency_raw": currency,
            "channel_raw": "store",
            "source_file": filename,
            "source_format": "edi",
        })
    if not rows:
        return _empty_frame()
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
def parse_any(content: bytes, filename: str) -> pd.DataFrame:
    """Auto-detect format from filename / content sniff."""
    name = filename.lower()
    if name.endswith(".csv"):
        return parse_csv(content, filename)
    if name.endswith(".json") or name.endswith(".jsonl"):
        return parse_json(content, filename)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return parse_xlsx(content, filename)
    if name.endswith(".txt") or name.endswith(".edi"):
        # Sniff: pipe-delimited HDR/LIN = EDI; otherwise try JSON-lines
        head = content[:200].decode("utf-8", errors="replace")
        if "HDR|" in head or "LIN|" in head:
            return parse_edi(content, filename)
        if head.strip().startswith("{"):
            return parse_json(content, filename)
        return parse_edi(content, filename)
    # Last resort: try CSV then JSON
    try:
        return parse_csv(content, filename)
    except Exception:
        return parse_json(content, filename)
