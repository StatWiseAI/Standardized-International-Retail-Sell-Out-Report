"""Page 1 — Executive Summary: KPI Scorecard + Top Movers + Weekly Trend."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import plotly.express as px
import streamlit as st

from core.utils import (
    get_state_fact, get_state_dq, apply_filters,
    fmt_eur, fmt_int, fmt_pct,
)
from core.kpis import kpi_scorecard, top_movers, weekly_trend


st.set_page_config(page_title="Executive Summary", page_icon="📈", layout="wide")
st.title("Executive Summary")
st.caption("KPI scorecard, top movers and weekly trend across all loaded POS sources.")

fact = get_state_fact()
dq = get_state_dq()

if fact is None or fact.empty:
    st.warning("No data loaded. Please upload files or enable sample data on the main page.")
    st.stop()

# -- Global filters ---------------------------------------------------------
with st.expander("Filters", expanded=False):
    f1, f2, f3 = st.columns(3)
    countries = f1.multiselect("Country", sorted(fact["country"].dropna().unique()))
    partners = f2.multiselect("Partner", sorted(fact["partner"].dropna().unique()))
    channels = f3.multiselect("Channel", sorted(fact["channel"].dropna().unique()))

filtered = apply_filters(
    fact, {"countries": countries, "partners": partners, "channels": channels}
)

# -- KPI scorecard ----------------------------------------------------------
scores = kpi_scorecard(filtered, dq_score=dq.get("dq_score"))
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Net Sales", fmt_eur(scores["net_sales"]))
c2.metric("Units Sold", fmt_int(scores["units_sold"]))
c3.metric("Promo Share", fmt_pct(scores["promo_share_pct"]))
c4.metric("WoW Growth", fmt_pct(scores["wow_growth_pct"]))
c5.metric("Return Rate", fmt_pct(scores["return_rate_pct"]))
c6.metric("DQ Score", fmt_pct(scores["dq_score_pct"]))

st.divider()

# -- Weekly trend -----------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader("Weekly Net Sales")
    trend = weekly_trend(filtered)
    if trend.empty:
        st.info("Not enough data to display weekly trend.")
    else:
        trend["week_label"] = (
            trend["iso_year"].astype(str) + "-W" + trend["iso_week"].astype(str).str.zfill(2)
        )
        fig = px.line(
            trend, x="week_label", y="net_sales",
            markers=True,
            labels={"week_label": "ISO Week", "net_sales": "Net Sales (EUR)"},
        )
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top Movers (WoW)")
    movers = top_movers(filtered, by="brand_final", n=5)
    if movers.empty:
        st.info("Need at least two ISO weeks to compute movers.")
    else:
        movers = movers.rename(columns={
            "brand_final": "Brand",
            "delta_eur": "Δ EUR",
            "delta_pct": "Δ %",
        })
        st.dataframe(
            movers[["Brand", "Δ EUR", "Δ %"]].round(2),
            use_container_width=True, hide_index=True,
        )

st.divider()

# -- Commentary -------------------------------------------------------------
st.subheader("Management Commentary")
total = scores["net_sales"]
ret = scores["return_rate_pct"]
promo = scores["promo_share_pct"]
dq_pct = scores["dq_score_pct"] or 0

bullets = []
bullets.append(f"Total Net Sales reached **{fmt_eur(total)}** across the loaded sources.")
if promo:
    bullets.append(f"Promotion contributed **{fmt_pct(promo)}** of Net Sales — review pricing discipline if elevated.")
if ret:
    bullets.append(f"Returns currently represent **{fmt_pct(ret)}** of units sold.")
if dq_pct:
    flag = "green" if dq_pct >= 90 else ("amber" if dq_pct >= 75 else "red")
    bullets.append(f"Data-Quality status is **{flag.upper()}** at {fmt_pct(dq_pct)}.")

for b in bullets:
    st.markdown(f"- {b}")
