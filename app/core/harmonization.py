"""Harmonization layer: normalize dates, decimals, IDs, promos, returns."""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Date parsing — supports the case-study formats
# ---------------------------------------------------------------------------
_DATE_PATTERNS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%Y%m%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]


def parse_date(value) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NaT
    s = str(value).strip()
    if not s:
        return pd.NaT
    # Truncate timestamps to date portion for the fact grain
    for fmt in _DATE_PATTERNS:
        try:
            dt = pd.to_datetime(s, format=fmt, errors="raise")
            return dt.normalize()
        except (ValueError, TypeError):
            continue
    # Fallback: pandas best effort
    try:
        return pd.to_datetime(s, errors="coerce", dayfirst=("." in s)).normalize()
    except Exception:
        return pd.NaT


# ---------------------------------------------------------------------------
# Decimal normalization (DE comma vs EN dot, mixed strings)
# ---------------------------------------------------------------------------
def parse_decimal(value) -> float:
    if value is None:
        return np.nan
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return np.nan
    # Strip currency symbols, percent signs and spaces
    s = re.sub(r"[€$£\s%]", "", s)
    if "," in s and "." in s:
        # Assume the last separator is the decimal one
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


# ---------------------------------------------------------------------------
# Store ID normalization (DE-0102 / DE0102 / FR_221 / IT/078 ...)
# ---------------------------------------------------------------------------
_STORE_PREFIX_RE = re.compile(r"^([A-Z]{2})[\W_]?(\w+)$", re.IGNORECASE)


def normalize_store_id(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper().replace(" ", "")
    if not s:
        return None
    m = _STORE_PREFIX_RE.match(s)
    if m:
        country = m.group(1).upper()
        suffix = m.group(2)
        # If suffix is all digits → DE-0102 style
        if suffix.isdigit():
            return f"{country}-{suffix.zfill(4)}"
        # Otherwise keep the original separator family
        if "/" in s:
            return s.replace("_", "/").replace("-", "/")
        if "_" in s:
            return s.replace("-", "_")
        return f"{country}-{suffix}"
    return s


# ---------------------------------------------------------------------------
# SKU normalization (SKU-77881 / SKU77881 / 77881 → SKU-77881)
# ---------------------------------------------------------------------------
def normalize_sku(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    if not digits:
        return s
    return f"SKU-{digits}"


# ---------------------------------------------------------------------------
# Brand / category casing
# ---------------------------------------------------------------------------
def normalize_text(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s.title()


# ---------------------------------------------------------------------------
# Promo flag harmonization
# ---------------------------------------------------------------------------
def normalize_promo(promo_value, discount_value) -> (int, float):
    """Return (promo_flag, discount_pct_norm).

    Accepts inputs like 0.10, 10%, Y/N, DISC=10, True/False.
    """
    disc = parse_decimal(discount_value)
    if not np.isnan(disc):
        # Convert percentages > 1 to fractions
        if disc > 1:
            disc = disc / 100.0
    flag = 0
    if promo_value is not None:
        s = str(promo_value).strip().upper()
        if s in {"Y", "YES", "TRUE", "1"}:
            flag = 1
        elif s in {"N", "NO", "FALSE", "0"}:
            flag = 0
    if not np.isnan(disc) and disc > 0:
        flag = 1
    return flag, (0.0 if np.isnan(disc) else float(disc))


# ---------------------------------------------------------------------------
# Pipeline entrypoint
# ---------------------------------------------------------------------------
def harmonize(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Convert a parser output frame into the canonical fact-ready frame."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()

    df["sale_date"] = df["sale_date_raw"].map(parse_date)
    df["store_id_canon"] = df["store_id_raw"].map(normalize_store_id)
    df["sku_canon"] = df["sku_raw"].map(normalize_sku)
    df["brand"] = df["brand_raw"].map(normalize_text)
    df["category"] = df["category_raw"].map(normalize_text)
    df["units"] = df["units_raw"].map(parse_decimal)
    df["net_sales_amt"] = df["net_sales_raw"].map(parse_decimal)
    df["gross_sales_amt"] = df["gross_sales_raw"].map(parse_decimal)

    promo_norm = df.apply(
        lambda r: normalize_promo(r.get("promo_raw"), r.get("discount_raw")),
        axis=1,
    )
    df["promo_flag"] = [p[0] for p in promo_norm]
    df["discount_pct_norm"] = [p[1] for p in promo_norm]

    df["return_flag"] = ((df["units"].fillna(0) < 0) |
                        (df["net_sales_amt"].fillna(0) < 0)).astype(int)

    df["currency"] = df["currency_raw"].fillna("EUR").astype(str).str.upper()
    df["channel"] = df["channel_raw"].fillna("store").astype(str).str.lower()
    df["iso_week"] = df["sale_date"].dt.isocalendar().week.fillna(0).astype(int)
    df["iso_year"] = df["sale_date"].dt.isocalendar().year.fillna(0).astype(int)

    # Mark unparseable rows but keep them for the DQ dashboard
    df["row_parseable"] = (
        df["sale_date"].notna()
        & df["store_id_canon"].notna()
        & df["sku_canon"].notna()
        & df["net_sales_amt"].notna()
    ).astype(int)

    return df
