"""Page 4 — Data Quality Dashboard."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.express as px
import streamlit as st

from core.utils import get_state_fact, get_state_dq, fmt_pct


st.set_page_config(page_title="Data Quality", page_icon="🛡️", layout="wide")
st.title("Data Quality Dashboard")
st.caption(
    "Completeness, conformity, plausibility, uniqueness and reconciliation across "
    "the loaded POS sources."
)

fact = get_state_fact()
dq = get_state_dq()

if fact is None or fact.empty or not dq:
    st.warning("No data loaded.")
    st.stop()


# -- Overall DQ score -------------------------------------------------------
score = dq.get("dq_score", 0.0)
flag_color = "#1F8F4D" if score >= 90 else ("#D58E00" if score >= 75 else "#C0392B")

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:1rem;">
      <div style="background:{flag_color}; color:white; padding:0.8rem 1.4rem;
                  border-radius:12px; font-size:1.6rem; font-weight:600;">
        DQ Score: {score:.2f}%
      </div>
      <div style="color:#5A6473;">
        Weighted across Completeness (30%), Conformity (25%),
        Plausibility (20%), Uniqueness (15%), Reconciliation (10%).
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# -- DQ dimension radar -----------------------------------------------------
dims = dq.get("dimensions", {})
if dims:
    dim_df = pd.DataFrame(
        {
            "Dimension": ["Completeness", "Conformity", "Plausibility",
                          "Uniqueness", "Reconciliation"],
            "Score": [
                dims.get("completeness", 0) * 100,
                dims.get("conformity", 0) * 100,
                dims.get("plausibility", 0) * 100,
                dims.get("uniqueness", 0) * 100,
                dims.get("reconciliation", 0) * 100,
            ],
        }
    )
    fig = px.line_polar(dim_df, r="Score", theta="Dimension", line_close=True)
    fig.update_traces(fill="toself", line_color="#1B3A5B")
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=420, margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -- Rule-by-rule table -----------------------------------------------------
st.subheader("Rule results")
rules = pd.DataFrame(dq.get("rules", []))
if not rules.empty:
    rules["violation_pct"] = (rules["violations"] / rules["total"].replace(0, 1) * 100).round(2)
    rules["status"] = rules["violation_pct"].map(
        lambda v: "🟢 OK" if v < 1 else ("🟠 Warning" if v < 5 else "🔴 Critical")
    )
    rules = rules.rename(columns={
        "rule": "Rule",
        "dimension": "Dimension",
        "violations": "Violations",
        "total": "Rows checked",
        "violation_pct": "Violation %",
        "status": "Status",
    })
    st.dataframe(rules, use_container_width=True, hide_index=True)

st.divider()

# -- Issue log --------------------------------------------------------------
st.subheader("Issue log (sample)")
issues = dq.get("issues", pd.DataFrame())
if isinstance(issues, pd.DataFrame) and not issues.empty:
    by_code = issues["issue_code"].value_counts().reset_index()
    by_code.columns = ["Issue code", "Count"]
    c1, c2 = st.columns([1, 2])
    with c1:
        st.dataframe(by_code, use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(
            issues.head(200), use_container_width=True, hide_index=True
        )
    st.download_button(
        "Download full issue log (CSV)",
        data=issues.to_csv(index=False).encode("utf-8"),
        file_name="dq_issues.csv",
        mime="text/csv",
    )
else:
    st.success("No issues detected.")

st.divider()

# -- Source-format breakdown -----------------------------------------------
st.subheader("Rows by source format")
src = (
    fact.groupby("source_format", dropna=False).size().reset_index(name="rows")
)
fig = px.bar(src, x="source_format", y="rows", color="source_format",
             labels={"source_format": "Source format", "rows": "Rows"})
fig.update_layout(showlegend=False, height=320, plot_bgcolor="#FFFFFF",
                  margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)
