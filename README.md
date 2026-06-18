# International POS Reporting Dashboard

A deployment-ready **Python + Streamlit** application for international POS (sell-out) reporting. The app is designed to process **heterogeneous, semi-structured POS source files** from multiple countries and formats, harmonize them into a unified analytical model, apply data-quality checks, and render a professional dashboard with four reporting views:

1. **Executive Summary** — KPI scorecards, weekly trend, top movers  
2. **Country / Partner Performance** — sales, units, returns, partner comparison  
3. **Category / Brand Drill-down** — category, brand and SKU performance  
4. **Data Quality Dashboard** — completeness, conformity, plausibility, uniqueness, reconciliation  

The app is intentionally built as an **upload-first workflow**: a user must upload either **individual POS files** or **one ZIP archive containing multiple country feeds** before the dashboard is displayed.

---

## 1. What this project includes

### Application layer
- `app/streamlit_app.py` — main Streamlit entrypoint
- `app/pages/` — the four dashboard pages
- `app/core/parsers.py` — CSV / JSON / XLSX / TXT-EDI parsing
- `app/core/harmonization.py` — date, decimal, store-ID, SKU, promo and return normalization
- `app/core/master_data.py` — master-data enrichment for stores, products, channels and countries
- `app/core/dq.py` — data-quality rules and issue logging
- `app/core/kpis.py` — KPI layer aligned with the case-study logic
- `app/core/utils.py` — upload expansion, ZIP handling, formatting and filters

### Data layer
- `data/master/` — reference dimensions required by the app
  - `dim_store.csv`
  - `dim_product.csv`
  - `dim_channel.csv`
  - `dim_country.csv`

### Data generation layer
- `scripts/generate_master_data.py` — rebuilds the reference dimensions
- `scripts/generate_pos_data.py` — generates realistic multi-country POS datasets for local use

---

## 2. Upload workflow

The application does **not** ship with bulky transactional datasets inside the repository.

Instead, the workflow is:

1. Open the Streamlit application
2. Upload either:
   - one or more POS files (`.csv`, `.json`, `.jsonl`, `.xlsx`, `.xls`, `.txt`, `.edi`), or
   - **one `.zip` archive** containing all country files in mixed formats
3. The app expands ZIP archives in memory
4. Each file is parsed and harmonized into a canonical transaction model
5. The data is enriched with store and product master data
6. Data-quality checks run automatically
7. KPIs are calculated and the four dashboard pages become available

This approach keeps the GitHub repository lightweight while still supporting **large local datasets**.

---

## 3. Supported source formats

The app can process formats similar to the original case-study examples:

- **CSV**
  - ISO dates: `2026-04-03`
  - alternative local dates: `03.04.2026`, `2026/04/04`
  - decimal styles with `.` or `,`
- **JSON / JSON-lines**
  - e.g. French tracking-log style with fields such as `dt`, `shop`, `sku`, `gross`, `net`
- **XLSX / Excel**
  - structured retail exports with the same business fields in tabular format
- **TXT / EDI-style feeds**
  - e.g. `HDR | LIN | TRL` pipe-delimited transaction files
- **ZIP packages**
  - one archive containing many country files and mixed formats

---

## 4. Harmonization logic

The application standardizes the following before reporting:

- **Dates**
  - `YYYY-MM-DD`
  - `DD.MM.YYYY`
  - `YYYY/MM/DD`
  - `YYYYMMDD`
  - ISO timestamps such as `2026-04-03T14:23:10`
- **Decimals**
  - comma vs. dot separators (`99,99` → `99.99`)
- **Store IDs**
  - e.g. `DE-0102`, `DE0102`, `FR_221`, `IT/078`
- **SKUs**
  - e.g. `SKU-77881`, `SKU77881`, `77881`
- **Promotion indicators**
  - e.g. `0.10`, `10%`, `Y/N`, `DISC=10`
- **Returns**
  - detected through negative units or negative sales amounts

The analytical fact grain is:

> **Date × Store × SKU × Channel × Promo × Source**

---

## 5. Analytical model

The project uses a practical reporting-oriented structure:

- **Raw upload handling**
- **Parsing / staging**
- **Harmonized core transaction layer**
- **Star-style reporting mart**

A **Star Schema** is the primary reporting model for this application. Snowflake normalization is intentionally avoided in the prototype except where a downstream extension would require it.

---

## 6. KPI definitions

| KPI | Formula |
|---|---|
| **Net Sales** | `Σ net_sales_amt` |
| **Units Sold** | `Σ max(units, 0)` |
| **Promo Share (%)** | `Σ Net Sales where promo_flag = 1 / Σ Net Sales × 100` |
| **WoW Growth (%)** | `(Net Sales W − Net Sales W-1) / Net Sales W-1 × 100` |
| **Return Rate (%)** | `abs(Σ min(units, 0)) / Σ max(units, 0) × 100` |
| **Data Quality Score (%)** | `100 × (0.30·C + 0.25·K + 0.20·P + 0.15·U + 0.10·R)` |

Where:
- `C` = Completeness
- `K` = Conformity
- `P` = Plausibility
- `U` = Uniqueness
- `R` = Reconciliation

---

## 7. Data-quality rules included

The DQ engine checks at least:

- parseable dates
- required-field completeness
- store mapping availability
- product mapping availability
- duplicate transactions
- sign consistency between units and net sales
- pricing plausibility against reference RRP

It produces:
- an overall **DQ score**
- a rule-by-rule summary
- an issue log with issue codes such as `STORE_UNMAPPED`, `SKU_UNMAPPED`, `DUPLICATE`, `PRICE_OUTLIER`

---

## 8. Local setup

```bash
git clone https://github.com/<your-user>/pos-dashboard.git
cd pos-dashboard
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

---

## 9. Generate large datasets locally

The repository does **not** include bulky transactional source files by default.

To generate realistic upload files locally:

```bash
python scripts/generate_master_data.py
python scripts/generate_pos_data.py --rows 2000000 --out generated_data
```

This creates **20+ country files** in mixed formats, suitable for:
- local performance testing
- packaging into a ZIP archive
- uploading into the app

Optional: compress the generated files into a ZIP package:

```bash
cd generated_data
zip -r pos_upload_bundle.zip .
```

Then upload `pos_upload_bundle.zip` in the Streamlit app.

---

## 10. Streamlit Cloud deployment

1. Push the repository to GitHub
2. Open [https://share.streamlit.io](https://share.streamlit.io)
3. Create a new app
4. Set the main file path to:

```text
app/streamlit_app.py
```

5. Deploy

Because the dashboard expects users to upload their own datasets, the repository stays lightweight and Streamlit Cloud remains practical to deploy.

---

## 11. Suggested Git strategy

Commit:
- application code
- master/reference data
- documentation
- generation scripts

Do **not** commit:
- multi-million-row generated POS files
- local upload bundles
- large archives created for testing

---

## 12. Project purpose

This project is intended as a **professional prototype of an international retail POS reporting application**:
- realistic enough for portfolio / interview demonstration
- modular enough for extension
- lightweight enough for GitHub and Streamlit Cloud deployment
