"""Data Quality engine.

Produces:
- a per-row DQ score
- a per-rule issue log
- an aggregate dictionary used by the DQ dashboard
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0
    return float(max(0.0, min(1.0, numerator / denominator)))


# ---------------------------------------------------------------------------
# Rule-level checks
# ---------------------------------------------------------------------------
def run_checks(fact: pd.DataFrame) -> Dict:
    """Run all DQ rules on a harmonized fact frame and return a summary dict."""
    if fact is None or fact.empty:
        return {
            "total_rows": 0,
            "rules": [],
            "dimensions": {
                "completeness": 1.0,
                "conformity": 1.0,
                "plausibility": 1.0,
                "uniqueness": 1.0,
                "reconciliation": 1.0,
            },
            "dq_score": 100.0,
            "issues": pd.DataFrame(),
        }

    n = len(fact)
    rules: List[Dict] = []
    issues_frames: List[pd.DataFrame] = []

    # Rule 1 — date parseable
    bad = fact["sale_date"].isna()
    rules.append({"rule": "Date parseable", "dimension": "Conformity",
                  "violations": int(bad.sum()), "total": n})
    if bad.any():
        issues_frames.append(_issue_frame(fact[bad], "DATE_UNPARSEABLE"))

    # Rule 2 — store mapped
    bad = fact.get("store_unmapped", pd.Series([False] * n)).astype(bool)
    rules.append({"rule": "Store mapped", "dimension": "Completeness",
                  "violations": int(bad.sum()), "total": n})
    if bad.any():
        issues_frames.append(_issue_frame(fact[bad], "STORE_UNMAPPED"))

    # Rule 3 — SKU mapped
    bad = fact.get("sku_unmapped", pd.Series([False] * n)).astype(bool)
    rules.append({"rule": "SKU mapped", "dimension": "Completeness",
                  "violations": int(bad.sum()), "total": n})
    if bad.any():
        issues_frames.append(_issue_frame(fact[bad], "SKU_UNMAPPED"))

    # Rule 4 — duplicate transactions
    dup_cols = ["sale_date", "store_id_canon", "sku_canon",
                "units", "net_sales_amt", "source_file"]
    have_cols = [c for c in dup_cols if c in fact.columns]
    dup = fact.duplicated(subset=have_cols, keep=False)
    rules.append({"rule": "Duplicate rows", "dimension": "Uniqueness",
                  "violations": int(dup.sum()), "total": n})
    if dup.any():
        issues_frames.append(_issue_frame(fact[dup], "DUPLICATE"))

    # Rule 5 — net sales sign consistent with units sign
    units = fact["units"].fillna(0)
    net = fact["net_sales_amt"].fillna(0)
    sign_mismatch = ((units > 0) & (net < 0)) | ((units < 0) & (net > 0))
    rules.append({"rule": "Sign consistency (units vs net)",
                  "dimension": "Plausibility",
                  "violations": int(sign_mismatch.sum()), "total": n})
    if sign_mismatch.any():
        issues_frames.append(_issue_frame(fact[sign_mismatch], "SIGN_MISMATCH"))

    # Rule 6 — price plausibility vs RRP (allow up to 2× RRP)
    if "rrp_eur" in fact.columns:
        unit_price = np.where(
            (units != 0), net.abs() / units.abs().replace(0, np.nan), np.nan
        )
        rrp = fact["rrp_eur"].astype(float)
        outlier = pd.Series(
            np.where(
                rrp.notna() & ~np.isnan(unit_price),
                (unit_price > rrp * 2.0) | (unit_price < rrp * 0.2),
                False,
            ),
            index=fact.index,
        )
        rules.append({"rule": "Unit price vs RRP plausibility",
                      "dimension": "Plausibility",
                      "violations": int(outlier.sum()), "total": n})
        if outlier.any():
            issues_frames.append(_issue_frame(fact[outlier], "PRICE_OUTLIER"))

    # Rule 7 — required field completeness
    required_missing = (
        fact["sale_date"].isna()
        | fact["store_id_canon"].isna()
        | fact["sku_canon"].isna()
        | fact["net_sales_amt"].isna()
    )
    rules.append({"rule": "Required fields complete",
                  "dimension": "Completeness",
                  "violations": int(required_missing.sum()), "total": n})
    if required_missing.any():
        issues_frames.append(_issue_frame(fact[required_missing], "REQUIRED_MISSING"))

    # ----------------------------------------------------------------
    # Dimension scores (each in [0,1])
    # ----------------------------------------------------------------
    completeness = _safe_ratio(n - int(required_missing.sum()), n)
    conformity = _safe_ratio(n - int(fact["sale_date"].isna().sum()), n)
    plausibility = _safe_ratio(n - int(sign_mismatch.sum()), n)
    uniqueness = _safe_ratio(n - int(dup.sum()), n)
    reconciliation = 1.0  # placeholder: would compare batch totals vs control sums

    dq_score = 100.0 * (
        0.30 * completeness
        + 0.25 * conformity
        + 0.20 * plausibility
        + 0.15 * uniqueness
        + 0.10 * reconciliation
    )

    issues = (
        pd.concat(issues_frames, ignore_index=True)
        if issues_frames
        else pd.DataFrame()
    )

    return {
        "total_rows": n,
        "rules": rules,
        "dimensions": {
            "completeness": completeness,
            "conformity": conformity,
            "plausibility": plausibility,
            "uniqueness": uniqueness,
            "reconciliation": reconciliation,
        },
        "dq_score": round(dq_score, 2),
        "issues": issues,
    }


def _issue_frame(rows: pd.DataFrame, code: str) -> pd.DataFrame:
    cols = [c for c in [
        "source_file", "sale_date", "store_id_canon", "sku_canon",
        "units", "net_sales_amt", "brand", "category"
    ] if c in rows.columns]
    out = rows[cols].copy()
    out["issue_code"] = code
    return out
