"""International POS Reporting Dashboard — main entrypoint.

Run locally:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys

# Make `core` importable when Streamlit launches this file directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from core.utils import (
    process_files,
    expand_uploaded_inputs,
    fmt_eur,
    fmt_int,
    fmt_pct,
)
from core.kpis import kpi_scorecard


st.set_page_config(
    page_title="POS Reporting Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <div style="padding: 1rem 0 0.5rem 0; border-bottom: 1px solid #E5E9F0;">
      <h1 style="margin-bottom: 0.2rem; color:#1B3A5B;">International POS Reporting Dashboard</h1>
      <p style="color:#5A6473; margin-top:0;">
        Upload individual POS files or one ZIP archive containing all country feeds.
        The application will parse, harmonize, validate and visualize the data automatically.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.header("1. Upload data")

    uploaded = st.file_uploader(
        "Upload POS files or a ZIP package",
        type=["zip", "csv", "json", "jsonl", "xlsx", "xls", "txt", "edi"],
        accept_multiple_files=True,
        help=(
            "Supported inputs: ZIP, CSV, JSON / JSON-lines, XLSX, TXT/EDI. "
            "ZIP archives can contain multiple country files and mixed formats."
        ),
    )

    if st.button(
        "Process upload",
        type="primary",
        use_container_width=True,
        disabled=not uploaded,
    ):
        expanded = expand_uploaded_inputs(uploaded)
        with st.spinner("Parsing, harmonizing and validating uploaded data..."):
            bundle = process_files(expanded)
        st.session_state["bundle"] = bundle
        st.success(
            f"Processed {len(bundle.get('files_processed', []))} supported file(s) "
            f"from {len(uploaded)} uploaded item(s)."
        )

    if st.button("Clear current dataset", use_container_width=True):
        st.session_state.pop("bundle", None)
        st.rerun()

    st.divider()
    st.caption("After processing, open the report pages from the left sidebar menu.")


bundle = st.session_state.get("bundle", {"fact": None, "dq": {}, "files_processed": []})
fact = bundle.get("fact")
dq = bundle.get("dq", {})


if fact is None or fact.empty:
    st.info(
        "Please upload one or more POS source files, or a ZIP archive containing all country feeds, "
        "before the dashboard is displayed."
    )

    st.markdown(
        """
        ### Expected inputs
        - **POS source files** in CSV, JSON / JSON-lines, XLSX, TXT or EDI-style text
        - **Single ZIP archive** containing multiple country files in mixed formats
        - Files similar to the case-study structure, e.g. Germany CSV, France JSON logs, Italy EDI text

        ### What the app does after upload
        1. Detects the source format per file
        2. Standardizes dates, decimal separators, store IDs and SKUs
        3. Enriches transactions with store and product master data
        4. Applies data-quality checks
        5. Computes KPIs and renders the four reporting pages
        """
    )
    st.stop()


scores = kpi_scorecard(fact, dq_score=dq.get("dq_score"))

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Net Sales", fmt_eur(scores["net_sales"]))
c2.metric("Units Sold", fmt_int(scores["units_sold"]))
c3.metric("Promo Share", fmt_pct(scores["promo_share_pct"]))
c4.metric("WoW Growth", fmt_pct(scores["wow_growth_pct"]))
c5.metric("Return Rate", fmt_pct(scores["return_rate_pct"]))
c6.metric("DQ Score", fmt_pct(scores["dq_score_pct"]))

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader("Processed source files")
    src = (
        fact.groupby(["source_format", "source_file"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    st.dataframe(src, use_container_width=True, hide_index=True)

with right:
    st.subheader("Upload status")
    st.metric("Uploaded items", len(uploaded) if uploaded else len(bundle.get("files_received", [])))
    st.metric("Files processed", len(bundle.get("files_processed", [])))
    st.metric("Fact rows", f"{len(fact):,}")

st.caption(
    "Use the pages in the left sidebar to open the four reporting views: "
    "Executive Summary, Country/Partner, Category/Brand, and Data Quality."
)
