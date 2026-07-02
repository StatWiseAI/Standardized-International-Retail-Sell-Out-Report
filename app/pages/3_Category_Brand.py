"""Page 3 — Category / Brand Drill-down."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import plotly.express as px
import streamlit as st

from core.utils import get_state_fact, apply_filters, fmt_eur, fmt_int, fmt_pct
from core.kpis import by_category_brand


st.set_page_config(page_title="Category / Brand", page_icon="🏷️", layout="wide")
st.title("Category / Brand Drill-down")
st.caption("Drill from category to brand to SKU. Promo and pricing context included.")

fact = get_state_fact()
if fact is None or fact.empty:
    st.warning("No data loaded.")
    st.stop()

with st.expander("Filters", expanded=False):
    f1, f2, f3, f4 = st.columns(4)
    countries = f1.multiselect("Country", sorted(fact["country"].dropna().unique()))
    partners = f2.multiselect("Partner", sorted(fact["partner"].dropna().unique()))
    categories = f3.multiselect(
        "Category", sorted(fact["category_final"].dropna().unique())
    )
    brands = f4.multiselect(
        "Brand", sorted(fact["brand_final"].dropna().unique())
    )

filtered = apply_filters(
    fact,
    {
        "countries": countries, "partners": partners,
        "categories": categories, "brands": brands,
    },
)

cat_brand = by_category_brand(filtered)

left, right = st.columns(2)

with left:
    st.subheader("Net Sales by Category")
    if not cat_brand.empty:
        agg = cat_brand.groupby("category_final", dropna=False)["net_sales"].sum().reset_index()
        agg = agg.sort_values("net_sales", ascending=True)
        fig = px.bar(
            agg, x="net_sales", y="category_final", orientation="h",
            labels={"net_sales": "Net Sales (EUR)", "category_final": "Category"},
            color="net_sales", color_continuous_scale="Teal",
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                          coloraxis_showscale=False, plot_bgcolor="#FFFFFF")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top 10 Brands by Net Sales")
    if not cat_brand.empty:
        agg = cat_brand.groupby("brand_final", dropna=False)["net_sales"].sum().reset_index()
        agg = agg.sort_values("net_sales", ascending=False).head(10).sort_values("net_sales")
        fig = px.bar(
            agg, x="net_sales", y="brand_final", orientation="h",
            labels={"net_sales": "Net Sales (EUR)", "brand_final": "Brand"},
            color="net_sales", color_continuous_scale="Blues",
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                          coloraxis_showscale=False, plot_bgcolor="#FFFFFF")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -- Category × Brand table ------------------------------------------------
st.subheader("Category × Brand detail")
if cat_brand.empty:
    st.info("No data to display.")
else:
    cat_brand["promo_share_pct"] = (
        (cat_brand["promo_sales"] / cat_brand["net_sales"].replace(0, 1)) * 100
    ).round(2)
    display = cat_brand.copy()
    display["net_sales"] = display["net_sales"].map(fmt_eur)
    display["units"] = display["units"].map(fmt_int)
    display["promo_sales"] = display["promo_sales"].map(fmt_eur)
    display["promo_share_pct"] = display["promo_share_pct"].map(fmt_pct)
    display = display.rename(columns={
        "category_final": "Category",
        "brand_final": "Brand",
        "net_sales": "Net Sales",
        "units": "Units",
        "promo_sales": "Promo Sales",
        "promo_share_pct": "Promo Share",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()

# -- SKU drill-down --------------------------------------------------------
st.subheader("SKU drill-down")
if filtered.empty:
    st.info("No data to display.")
else:
    sku = (
        filtered.groupby(
            ["sku_canon", "product_name", "brand_final", "category_final"],
            dropna=False,
        )
        .agg(
            net_sales=("net_sales_amt", "sum"),
            units=("units", lambda s: s.clip(lower=0).sum()),
            returns=("return_flag", "sum"),
        )
        .reset_index()
        .sort_values("net_sales", ascending=False)
        .head(50)
    )
    sku["net_sales"] = sku["net_sales"].map(fmt_eur)
    sku["units"] = sku["units"].map(fmt_int)
    sku = sku.rename(columns={
        "sku_canon": "SKU",
        "product_name": "Product",
        "brand_final": "Brand",
        "category_final": "Category",
        "net_sales": "Net Sales",
        "units": "Units",
        "returns": "Returns",
    })
    st.dataframe(sku, use_container_width=True, hide_index=True)

# Unmapped SKU callout
unmapped = filtered[filtered.get("sku_unmapped", False)]
if not unmapped.empty:
    st.warning(
        f"{len(unmapped):,} rows reference SKUs not present in the product master. "
        "These rows are visible on the Data Quality page."
    )
