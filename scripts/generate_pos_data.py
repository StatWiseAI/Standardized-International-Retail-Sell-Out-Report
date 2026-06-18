"""Generate realistic POS transaction data.

Outputs multi-format POS files into data/samples/:
- CSV (ISO dates, dot decimal)
- CSV-DE (DD.MM.YYYY, comma decimal)
- JSON-lines (mixed)
- XLSX (Excel)
- TXT/EDI (pipe-delimited HDR/LIN/TRL)

Realistic inconsistencies injected:
- 3+ date formats
- comma vs dot decimal separators
- store-ID inconsistencies (DE-0102 vs DE0102 vs DE_0102)
- SKU formatting variations (SKU-77881 / SKU77881 / 77881)
- negative units/sales (returns)
- duplicate transactions (~0.5%)
- unmapped stores (~1%) and unmapped SKUs (~0.3%)
- brand casing variations (Nike / NIKE / nike)
- promo flags in different formats (0.10, 10%, Y/N, DISC=10)
- pricing outliers vs RRP
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MASTER_DIR = ROOT / "data" / "master"
SAMPLES_DIR = ROOT / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

random.seed(7)
np.random.seed(7)


# ---------------------------------------------------------------------------
# Load master data
# ---------------------------------------------------------------------------
def load_masters():
    stores = pd.read_csv(MASTER_DIR / "dim_store.csv")
    products = pd.read_csv(MASTER_DIR / "dim_product.csv")
    return stores, products


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DATE_FORMATS_BY_COUNTRY = {
    "DE": "%d.%m.%Y",
    "AT": "%d.%m.%Y",
    "CH": "%d.%m.%Y",
    "FR": "%Y-%m-%dT%H:%M:%S",
    "IT": "%Y%m%d",
    "ES": "%Y/%m/%d",
    "PT": "%Y/%m/%d",
}
DEFAULT_DATE_FMT = "%Y-%m-%d"

PROMO_STYLE_BY_COUNTRY = {
    "DE": "pct_string",   # "10%"
    "FR": "yn",           # "Y" / "N"
    "IT": "disc_eq",      # DISC=10
    "ES": "decimal",      # 0.10
    "PT": "decimal",
    "AT": "pct_string",
    "CH": "pct_string",
}
DEFAULT_PROMO_STYLE = "decimal"


def fmt_number(value: float, country: str) -> str:
    """Format a number with country-specific decimal separator."""
    if country in {"DE", "AT", "CH", "FR", "IT", "ES", "PT"}:
        return f"{value:.2f}".replace(".", ",")
    return f"{value:.2f}"


def denormalize_store_id(store_id: str) -> str:
    """Occasionally drop the canonical separator to inject inconsistency."""
    if random.random() < 0.20:
        return store_id.replace("-", "").replace("_", "").replace("/", "")
    if random.random() < 0.05 and "-" in store_id:
        return store_id.replace("-", "_")
    return store_id


def denormalize_sku(sku: str) -> str:
    """Vary SKU formatting (SKU-77881 / SKU77881 / 77881)."""
    digits = "".join(c for c in sku if c.isdigit())
    style = random.choices(
        ["canonical", "no_dash", "digits_only"],
        weights=[0.80, 0.12, 0.08],
    )[0]
    if style == "no_dash":
        return f"SKU{digits}"
    if style == "digits_only":
        return digits
    return sku


def vary_brand(brand: str) -> str:
    """Inject casing inconsistencies."""
    r = random.random()
    if r < 0.10:
        return brand.upper()
    if r < 0.13:
        return brand.lower()
    return brand


# ---------------------------------------------------------------------------
# Row generator
# ---------------------------------------------------------------------------
def make_rows(n: int, stores: pd.DataFrame, products: pd.DataFrame,
              start_date: datetime, days: int) -> list:
    """Produce `n` raw POS transactions as dicts (pre-format)."""
    rows = []
    store_recs = stores.to_dict("records")
    product_recs = products.to_dict("records")
    store_weights = np.random.dirichlet(np.ones(len(store_recs)) * 0.6)
    product_weights = np.random.dirichlet(np.ones(len(product_recs)) * 0.5)

    store_idx = np.random.choice(len(store_recs), size=n, p=store_weights)
    product_idx = np.random.choice(len(product_recs), size=n, p=product_weights)
    day_offsets = np.random.randint(0, days, size=n)
    qty_pool = np.random.choice([1, 1, 1, 2, 2, 3, 4], size=n)

    for i in range(n):
        store = store_recs[store_idx[i]]
        product = product_recs[product_idx[i]]
        country = store["country"]
        sale_dt = start_date + timedelta(
            days=int(day_offsets[i]),
            hours=random.randint(8, 21),
            minutes=random.randint(0, 59),
        )

        units = int(qty_pool[i])
        # Pricing: base RRP with random discount, occasional outlier
        rrp = float(product["rrp_eur"])
        discount_pct = random.choices(
            [0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30],
            weights=[0.40, 0.10, 0.05, 0.10, 0.15, 0.10, 0.05, 0.05],
        )[0]
        unit_price = rrp * (1 - discount_pct)

        # Pricing outlier (~0.2%)
        if random.random() < 0.002:
            unit_price = rrp * random.choice([0.05, 3.0, 5.0])

        net = round(unit_price * units, 2)
        gross = round(rrp * units, 2)

        # Return (~3%)
        if random.random() < 0.03:
            units = -1
            net = -round(unit_price, 2)
            gross = -round(rrp, 2)

        rows.append({
            "sale_dt": sale_dt,
            "country": country,
            "store_id_canon": store["store_id_canon"],
            "sku_canon": product["sku_canon"],
            "brand": product["brand_canon"],
            "category": product["category_canon"],
            "units": units,
            "gross_sales": gross,
            "net_sales": net,
            "discount_pct": round(discount_pct, 2),
            "promo_flag": 1 if discount_pct > 0 else 0,
            "channel": store["default_channel"],
            "currency": "EUR",
        })

    # Duplicates (~0.5%)
    n_dup = int(n * 0.005)
    if n_dup > 0:
        dup_idx = np.random.choice(len(rows), size=n_dup, replace=False)
        for j in dup_idx:
            rows.append(dict(rows[j]))

    # Unmapped stores (~1%)
    n_unmapped = int(n * 0.01)
    for _ in range(n_unmapped):
        rows.append({
            **rows[random.randint(0, len(rows) - 1)],
            "store_id_canon": f"XX-{random.randint(1, 999):04d}",
        })

    # Unmapped SKUs (~0.3%)
    n_unmapped_sku = int(n * 0.003)
    for _ in range(n_unmapped_sku):
        rows.append({
            **rows[random.randint(0, len(rows) - 1)],
            "sku_canon": f"SKU-{random.randint(90000, 99999)}",
        })

    return rows


# ---------------------------------------------------------------------------
# Writers — one per source format
# ---------------------------------------------------------------------------
def write_csv_de(rows, path):
    """German CSV: DD.MM.YYYY dates, comma decimals, mixed store-id formats."""
    lines = ["sale_date,store_id,store_name,sku,brand,category,units,net_sales,discount_pct,currency,channel"]
    for r in rows:
        sale = r["sale_dt"].strftime("%d.%m.%Y")
        sid = denormalize_store_id(r["store_id_canon"])
        sku = denormalize_sku(r["sku_canon"])
        brand = vary_brand(r["brand"])
        # Promo style: "10%" or empty
        if r["promo_flag"] == 1:
            promo_str = f"{int(r['discount_pct']*100)}%"
        else:
            promo_str = "0"
        net = fmt_number(r["net_sales"], "DE")
        lines.append(
            f"{sale},{sid},SPORT2000,{sku},{brand},{r['category']},"
            f"{r['units']},{net},{promo_str},EUR,{r['channel']}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv_iso(rows, path):
    """ISO CSV: YYYY-MM-DD dates, dot decimals, decimal discount."""
    lines = ["sale_date,store_id,store_name,sku,brand,category,units,net_sales,discount_pct,currency,channel"]
    for r in rows:
        sale = r["sale_dt"].strftime("%Y-%m-%d")
        sid = denormalize_store_id(r["store_id_canon"])
        sku = denormalize_sku(r["sku_canon"])
        brand = vary_brand(r["brand"])
        lines.append(
            f"{sale},{sid},SPORT2000,{sku},{brand},{r['category']},"
            f"{r['units']},{r['net_sales']:.2f},{r['discount_pct']:.2f},EUR,{r['channel']}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json_lines(rows, path):
    """FR-style JSON tracking log."""
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            sid = denormalize_store_id(r["store_id_canon"])
            sku = denormalize_sku(r["sku_canon"])
            promo = "Y" if r["promo_flag"] == 1 else "N"
            gross_str = fmt_number(r["gross_sales"], "FR")
            net_str = fmt_number(r["net_sales"], "FR")
            rec = {
                "dt": r["sale_dt"].strftime("%Y-%m-%dT%H:%M:%S"),
                "shop": sid,
                "sku": sku,
                "qty": str(r["units"]),
                "gross": gross_str,
                "net": net_str,
                "cur": "EUR",
                "promo": promo,
                "cat": r["category"],
                "brand": vary_brand(r["brand"]),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_xlsx(rows, path):
    """ES/PT-style Excel: YYYY/MM/DD, dot decimals."""
    data = []
    for r in rows:
        data.append({
            "sale_date": r["sale_dt"].strftime("%Y/%m/%d"),
            "store_id": denormalize_store_id(r["store_id_canon"]),
            "sku": denormalize_sku(r["sku_canon"]),
            "brand": vary_brand(r["brand"]),
            "category": r["category"],
            "units": r["units"],
            "net_sales": r["net_sales"],
            "discount_pct": r["discount_pct"],
            "currency": "EUR",
            "channel": r["channel"],
            "promo": r["promo_flag"],
        })
    pd.DataFrame(data).to_excel(path, index=False)


def write_edi(rows, path, country):
    """IT-style EDI: HDR/LIN/TRL pipe-delimited, YYYYMMDD."""
    lines = [f"HDR|{country}|W{rows[0]['sale_dt'].isocalendar().week:02d}|"
             f"{rows[0]['sale_dt'].strftime('%Y%m%d')}-"
             f"{rows[-1]['sale_dt'].strftime('%Y%m%d')}|EUR"]
    n_lines = 0
    for r in rows:
        sid = denormalize_store_id(r["store_id_canon"])
        sku = denormalize_sku(r["sku_canon"])
        disc = int(r["discount_pct"] * 100)
        sale = r["sale_dt"].strftime("%Y%m%d")
        net = f"{r['net_sales']:.2f}"
        lines.append(
            f"LIN|{sale}|{sid}|{sku}|{r['brand'].upper()}|"
            f"{r['category'].upper()}|QTY={r['units']}|NET={net}|DISC={disc}"
        )
        n_lines += 1
    lines.append(f"TRL|{n_lines}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Country → writer routing
# ---------------------------------------------------------------------------
COUNTRY_WRITER = {
    "DE": ("csv", write_csv_de),
    "AT": ("csv", write_csv_de),
    "CH": ("csv", write_csv_de),
    "FR": ("json", write_json_lines),
    "BE": ("json", write_json_lines),
    "NL": ("json", write_json_lines),
    "IE": ("json", write_json_lines),
    "IT": ("txt", write_edi),
    "GR": ("txt", write_edi),
    "HR": ("txt", write_edi),
    "SI": ("txt", write_edi),
    "ES": ("xlsx", write_xlsx),
    "PT": ("xlsx", write_xlsx),
    "PL": ("csv", write_csv_iso),
    "CZ": ("csv", write_csv_iso),
    "SK": ("csv", write_csv_iso),
    "HU": ("csv", write_csv_iso),
    "RO": ("csv", write_csv_iso),
    "BG": ("csv", write_csv_iso),
    "SE": ("json", write_json_lines),
    "DK": ("json", write_json_lines),
    "NO": ("json", write_json_lines),
    "FI": ("json", write_json_lines),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=2_000_000,
                    help="Total number of POS rows across all countries.")
    ap.add_argument("--days", type=int, default=28,
                    help="Time window length in days.")
    ap.add_argument("--start", type=str, default="2026-04-01",
                    help="Start date (YYYY-MM-DD).")
    ap.add_argument("--out", type=str, default=str(ROOT / "generated_data"),
                    help="Output directory for generated POS files.")
    ap.add_argument("--week", type=int, default=14,
                    help="ISO week label used in filenames.")
    ap.add_argument("--small", action="store_true",
                    help="Only generate small sample files (~20K rows total).")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    stores, products = load_masters()
    start_date = datetime.strptime(args.start, "%Y-%m-%d")

    total_rows = 20_000 if args.small else args.rows
    countries = sorted(stores["country"].unique())

    # Distribute rows roughly proportional to store count per country
    store_counts = stores.groupby("country").size().to_dict()
    total_stores = sum(store_counts.values())
    per_country = {
        c: max(500, int(total_rows * store_counts[c] / total_stores))
        for c in countries
    }

    print(f"Generating ~{sum(per_country.values()):,} rows across "
          f"{len(countries)} countries")

    for country in countries:
        c_stores = stores[stores["country"] == country]
        n_rows = per_country[country]
        rows = make_rows(n_rows, c_stores, products, start_date, args.days)
        rows.sort(key=lambda r: r["sale_dt"])

        ext, writer = COUNTRY_WRITER.get(country, ("csv", write_csv_iso))
        fname = f"pos_{country}_week{args.week:02d}.{ext}"
        out_path = out_dir / fname
        if ext == "txt":
            writer(rows, out_path, country)
        else:
            writer(rows, out_path)
        print(f"  {country}: {len(rows):>8,} rows → {fname}")

    print(f"\nDone. Files in {out_dir}")


if __name__ == "__main__":
    main()
