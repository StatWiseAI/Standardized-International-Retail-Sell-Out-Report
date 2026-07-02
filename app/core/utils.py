"""Shared utilities: formatting, upload expansion, caching and filters."""
from __future__ import annotations

import io
import zipfile
from typing import Iterable, List, Sequence, Tuple

import pandas as pd
import streamlit as st

from .parsers import parse_any
from .harmonization import harmonize
from .master_data import enrich_with_master
from .dq import run_checks

SUPPORTED_EXTENSIONS = {".csv", ".json", ".jsonl", ".xlsx", ".xls", ".txt", ".edi"}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def fmt_eur(value: float) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"€{value/1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"€{value/1_000:,.1f}K"
    return f"€{value:,.2f}"



def fmt_int(value: float) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}"



def fmt_pct(value: float) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.2f}%"


# ---------------------------------------------------------------------------
# Upload expansion
# ---------------------------------------------------------------------------
def _is_supported_file(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS)



def expand_uploaded_inputs(files: Sequence) -> List[Tuple[str, bytes]]:
    """Expand uploaded files.

    Accepts a list of Streamlit UploadedFile objects or `(filename, bytes)` tuples.
    Zip archives are expanded in memory; only supported file types are kept.
    """
    expanded: List[Tuple[str, bytes]] = []
    for item in files or []:
        if isinstance(item, tuple):
            filename, content = item
        else:
            filename, content = item.name, item.read()

        lower = filename.lower()
        if lower.endswith(".zip"):
            expanded.extend(_expand_zip_bytes(content, archive_name=filename))
        elif _is_supported_file(filename):
            expanded.append((filename, content))
    return expanded



def _expand_zip_bytes(content: bytes, archive_name: str) -> List[Tuple[str, bytes]]:
    out: List[Tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            member_name = member.filename
            # Skip macOS/system metadata
            if member_name.startswith("__MACOSX/") or member_name.endswith(".DS_Store"):
                continue
            short_name = member_name.split("/")[-1]
            if not _is_supported_file(short_name):
                continue
            out.append((short_name, zf.read(member)))
    return out


# ---------------------------------------------------------------------------
# Pipeline: uploaded bytes → fact frame + DQ summary
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_files(files: List[Tuple[str, bytes]]) -> dict:
    """`files` is a list of `(filename, bytes)` tuples after zip expansion."""
    frames = []
    processed_names = []
    for filename, content in files:
        raw = parse_any(content, filename)
        harm = harmonize(raw)
        if not harm.empty:
            frames.append(harm)
            processed_names.append(filename)
    if not frames:
        return {
            "fact": pd.DataFrame(),
            "dq": {},
            "files_processed": [],
            "files_received": [f[0] for f in files],
        }
    fact = pd.concat(frames, ignore_index=True)
    fact = enrich_with_master(fact)
    dq = run_checks(fact)
    return {
        "fact": fact,
        "dq": dq,
        "files_processed": processed_names,
        "files_received": [f[0] for f in files],
    }


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df
    if filters.get("countries"):
        out = out[out["country"].isin(filters["countries"])]
    if filters.get("partners"):
        out = out[out["partner"].isin(filters["partners"])]
    if filters.get("categories"):
        out = out[out["category_final"].isin(filters["categories"])]
    if filters.get("brands"):
        out = out[out["brand_final"].isin(filters["brands"])]
    if filters.get("channels"):
        out = out[out["channel"].isin(filters["channels"])]
    if filters.get("weeks"):
        out = out[out["iso_week"].isin(filters["weeks"])]
    return out



def get_state_fact() -> pd.DataFrame:
    bundle = st.session_state.get("bundle", {"fact": pd.DataFrame(), "dq": {}})
    return bundle.get("fact", pd.DataFrame())



def get_state_dq() -> dict:
    bundle = st.session_state.get("bundle", {"fact": pd.DataFrame(), "dq": {}})
    return bundle.get("dq", {})
