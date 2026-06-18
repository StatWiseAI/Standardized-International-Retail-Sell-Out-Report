# Data folder

This repository intentionally includes **reference/master data only**.

Large transactional POS datasets are **not bundled** with the project in order to keep the GitHub repository lightweight and deployment-friendly.

## Included
- `master/` — store, product, country and channel reference data required by the application

## Not included
- multi-country transactional POS files
- generated 2M+ row test datasets
- upload bundles / ZIP archives

## How to create local test data
Use:

```bash
python scripts/generate_master_data.py
python scripts/generate_pos_data.py --rows 2000000 --out generated_data
```

You can then upload the generated files directly in the app, or compress them into one ZIP file and upload the ZIP package.
