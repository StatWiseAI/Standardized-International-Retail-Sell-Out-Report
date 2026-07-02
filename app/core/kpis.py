"""KPI calculation layer — strictly aligned with the case-study definitions.

KPI formulas
------------
Net Sales        = Σ net_sales_amt
Units Sold       = Σ max(units, 0)
Promo Share (%)  = Σ Net Sales (promo_flag=1) / Σ Net Sales × 100
WoW Growth (%)   = (Net Sales_W − Net Sales_{W-1}) / Net Sales_{W-1} × 100
Return Rate (%)  = |Σ min(units, 0)| / Σ max(units, 0) × 100
DQ Score (%)     = 100 × (0.30·C + 0.25·K + 0.20·P + 0.15·U + 0.10·R)
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Core KPIs
# ---------------------------------------------------------------------------
def net_sales(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    return float(df["net_sales_amt"].fillna(0).sum())


def units_sold(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    return float(df["units"].clip(lower=0).fillna(0).sum())


def promo_share(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    total = net_sales(df)
    if total == 0:
        return 0.0
    promo = float(
        df.loc[df["promo_flag"] == 1, "net_sales_amt"].fillna(0).sum()
    )
    return round(promo / total * 100.0, 2)


def return_rate(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 0.0
    positives = df["units"].clip(lower=0).fillna(0).sum()
    negatives = df["units"].clip(upper=0).fillna(0).sum()
    if positives == 0:
        return 0.0
    return round(abs(negatives) / positives * 100.0, 2)


def wow_growth(df: pd.DataFrame, current_week: Optional[int] = None) -> float:
    """Week-over-week growth based on iso_week."""
    if df is None or df.empty or "iso_week" not in df.columns:
        return 0.0
    weeks = sorted(w for w in df["iso_week"].unique() if w and w > 0)
    if len(weeks) < 2:
        return 0.0
    if current_week is None:
        current_week = weeks[-1]
    if current_week not in weeks:
        return 0.0
    idx = weeks.index(current_week)
    if idx == 0:
        return 0.0
    prev_week = weeks[idx - 1]
    curr = float(df.loc[df["iso_week"] == current_week, "net_sales_amt"].sum())
    prev = float(df.loc[df["iso_week"] == prev_week, "net_sales_amt"].sum())
    if prev == 0:
        return 0.0
    return round((curr - prev) / prev * 100.0, 2)


# ---------------------------------------------------------------------------
# KPI scorecard
# ---------------------------------------------------------------------------
def kpi_scorecard(df: pd.DataFrame, dq_score: float = None) -> Dict[str, float]:
    return {
        "net_sales": net_sales(df),
        "units_sold": units_sold(df),
        "promo_share_pct": promo_share(df),
        "wow_growth_pct": wow_growth(df),
        "return_rate_pct": return_rate(df),
        "dq_score_pct": float(dq_score) if dq_score is not None else None,
    }


# ---------------------------------------------------------------------------
# Top movers (positive and negative)
# ---------------------------------------------------------------------------
def top_movers(df: pd.DataFrame, by: str = "brand_final", n: int = 5) -> pd.DataFrame:
    """Return top positive and negative movers by WoW net-sales delta."""
    if df is None or df.empty or by not in df.columns:
        return pd.DataFrame()
    weeks = sorted(w for w in df["iso_week"].unique() if w and w > 0)
    if len(weeks) < 2:
        return pd.DataFrame()
    curr_week, prev_week = weeks[-1], weeks[-2]

    curr = (
        df.loc[df["iso_week"] == curr_week]
        .groupby(by)["net_sales_amt"].sum()
        .rename("net_sales_curr")
    )
    prev = (
        df.loc[df["iso_week"] == prev_week]
        .groupby(by)["net_sales_amt"].sum()
        .rename("net_sales_prev")
    )
    out = pd.concat([curr, prev], axis=1).fillna(0)
    out["delta_eur"] = out["net_sales_curr"] - out["net_sales_prev"]
    out["delta_pct"] = np.where(
        out["net_sales_prev"] != 0,
        (out["delta_eur"] / out["net_sales_prev"]) * 100,
        np.nan,
    )
    out = out.sort_values("delta_eur", ascending=False)
    movers = pd.concat([out.head(n), out.tail(n)]).reset_index()
    return movers


# ---------------------------------------------------------------------------
# Aggregations used by dashboard pages
# ---------------------------------------------------------------------------
def by_country(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    g = (
        df.groupby(["country", "partner"], dropna=False)
        .agg(
            net_sales=("net_sales_amt", "sum"),
            units=("units", lambda s: s.clip(lower=0).sum()),
            returns=("return_flag", "sum"),
            rows=("net_sales_amt", "size"),
        )
        .reset_index()
    )
    g["return_rate_pct"] = np.where(
        g["units"] > 0, (g["returns"] / g["units"]) * 100, 0
    ).round(2)
    return g.sort_values("net_sales", ascending=False)


def by_category_brand(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return (
        df.groupby(["category_final", "brand_final"], dropna=False)
        .agg(
            net_sales=("net_sales_amt", "sum"),
            units=("units", lambda s: s.clip(lower=0).sum()),
            promo_sales=(
                "net_sales_amt",
                lambda s: s[df.loc[s.index, "promo_flag"] == 1].sum(),
            ),
        )
        .reset_index()
        .sort_values("net_sales", ascending=False)
    )


def weekly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return (
        df.groupby(["iso_year", "iso_week"], dropna=False)
        .agg(
            net_sales=("net_sales_amt", "sum"),
            units=("units", lambda s: s.clip(lower=0).sum()),
        )
        .reset_index()
        .sort_values(["iso_year", "iso_week"])
    )
