"""Master data loader for stores, products, channels and countries."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict

import pandas as pd

MASTER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "master")


@lru_cache(maxsize=1)
def load_dim_store() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(MASTER_DIR, "dim_store.csv"))
    df["store_id_canon"] = df["store_id_canon"].astype(str).str.strip()
    return df


@lru_cache(maxsize=1)
def load_dim_product() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(MASTER_DIR, "dim_product.csv"))
    df["sku_canon"] = df["sku_canon"].astype(str).str.strip()
    return df


@lru_cache(maxsize=1)
def load_dim_channel() -> pd.DataFrame:
    return pd.read_csv(os.path.join(MASTER_DIR, "dim_channel.csv"))


@lru_cache(maxsize=1)
def load_dim_country() -> pd.DataFrame:
    return pd.read_csv(os.path.join(MASTER_DIR, "dim_country.csv"))


def enrich_with_master(df: pd.DataFrame) -> pd.DataFrame:
    """Left-join fact data with master dimensions and flag unmapped rows."""
    store = load_dim_store()
    product = load_dim_product()

    df = df.merge(
        store[["store_id_canon", "store_name", "country", "region", "partner"]],
        on="store_id_canon",
        how="left",
        suffixes=("", "_dim"),
    )
    df = df.merge(
        product[["sku_canon", "product_name", "brand_canon", "category_canon", "rrp_eur"]],
        on="sku_canon",
        how="left",
        suffixes=("", "_dim"),
    )

    df["store_unmapped"] = df["country"].isna()
    df["sku_unmapped"] = df["product_name"].isna()

    # Prefer master-data brand/category when available
    df["brand_final"] = df["brand_canon"].fillna(df.get("brand"))
    df["category_final"] = df["category_canon"].fillna(df.get("category"))
    return df
