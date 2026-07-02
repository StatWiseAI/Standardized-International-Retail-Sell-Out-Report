"""Page 2 — Country / Partner Performance."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import plotly.express as px
import streamlit as st

from core.utils import get_state_fact, apply_filters, fmt_eur, fmt_int, fmt_pct
from core.kpis import by_country


st.set_page_config(page_title="Country / Partner", page_icon="🌍", layout="wide")
st.title("Country / Partner Performance")
st.caption("Compare countries and partners on Net Sales, Units, Promo, Returns and DQ.")

fact = get_state_fact()
if fact is None or fact.empty:
    st.warning("No data loaded.")
    st.stop()

with st.expander("Filters", expanded=False):
    f1, f2, f3 = st.columns(3)
    countries = f1.multiselect("Country", sorted(fact["country"].dropna().unique()))
    partners = f2.multiselect("Partner", sorted(fact["partner"].dropna().unique()))
    channels = f3.multiselect("Channel", sorted(fact["channel"].dropna().unique()))

filtered = apply_filters(
    fact, {"countries": countries, "partners": partners, "channels": channels}
)

# -- Country aggregation ----------------------------------------------------
country_df = by_country(filtered)

left, right = st.columns(2)

with left:
    st.subheader("Net Sales by Country")
    if not country_df.empty:
        agg = country_df.groupby("country", dropna=False)["net_sales"].sum().reset_index()
        agg = agg.sort_values("net_sales", ascending=True)
        fig = px.bar(
            agg, x="net_sales", y="country", orientation="h",
            labels={"net_sales": "Net Sales (EUR)", "country": "Country"},
            color="net_sales", color_continuous_scale="Blues",
        )
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10),
                          coloraxis_showscale=False, plot_bgcolor="#FFFFFF")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Return Rate by Country")
    if not country_df.empty:
        agg = (
            country_df.groupby("country", dropna=False)
            .agg(units=("units", "sum"), returns=("returns", "sum"))
            .reset_index()
        )
        agg["return_rate_pct"] = (agg["returns"] / agg["units"].replace(0, 1)) * 100
        fig = px.bar(
            agg.sort_values("return_rate_pct", ascending=True),
            x="return_rate_pct", y="country", orientation="h",
            labels={"return_rate_pct": "Return Rate (%)", "country": "Country"},
            color="return_rate_pct", color_continuous_scale="Reds",
        )
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10),
                          coloraxis_showscale=False, plot_bgcolor="#FFFFFF")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -- Country × Partner table ------------------------------------------------
st.subheader("Country × Partner detail")
if country_df.empty:
    st.info("No data to display.")
else:
    display = country_df.copy()
    display["net_sales"] = display["net_sales"].map(fmt_eur)
    display["units"] = display["units"].map(fmt_int)
    display["return_rate_pct"] = display["return_rate_pct"].map(fmt_pct)
    display = display.rename(columns={
        "country": "Country",
        "partner": "Partner",
        "net_sales": "Net Sales",
        "units": "Units",
        "returns": "Returns",
        "return_rate_pct": "Return Rate",
        "rows": "Rows",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

# -- Unmapped stores callout -----------------------------------------------
unmapped = filtered[filtered.get("store_unmapped", False)]
if not unmapped.empty:
    st.warning(
        f"{len(unmapped):,} rows reference stores not present in the master mapping. "
        "These rows are kept and visible in the Data Quality page."
    )
