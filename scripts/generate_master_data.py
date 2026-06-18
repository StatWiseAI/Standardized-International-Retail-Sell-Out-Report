"""Generate the master/reference data: stores, products, channels, countries.

Outputs go to data/master/.
Covers 20+ European countries with realistic store and product master data.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MASTER_DIR = ROOT / "data" / "master"
MASTER_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ---------------------------------------------------------------------------
# Countries (20+)
# ---------------------------------------------------------------------------
COUNTRIES = [
    # iso, name,             region,        partner
    ("DE", "Germany",        "DE-Mitte",    "PartnerA"),
    ("FR", "France",         "FR-Nord",     "PartnerB"),
    ("IT", "Italy",          "IT-Nord",     "PartnerC"),
    ("ES", "Spain",          "ES-Centro",   "PartnerD"),
    ("NL", "Netherlands",    "NL-West",     "PartnerB"),
    ("BE", "Belgium",        "BE-Vlaams",   "PartnerB"),
    ("AT", "Austria",        "AT-Ost",      "PartnerA"),
    ("CH", "Switzerland",    "CH-Zentral",  "PartnerA"),
    ("PL", "Poland",         "PL-Center",   "PartnerE"),
    ("CZ", "Czechia",        "CZ-Praha",    "PartnerE"),
    ("SK", "Slovakia",       "SK-West",     "PartnerE"),
    ("HU", "Hungary",        "HU-Central",  "PartnerE"),
    ("SE", "Sweden",         "SE-South",    "PartnerF"),
    ("DK", "Denmark",        "DK-Hov",      "PartnerF"),
    ("NO", "Norway",         "NO-Ost",      "PartnerF"),
    ("FI", "Finland",        "FI-South",    "PartnerF"),
    ("PT", "Portugal",       "PT-Lisboa",   "PartnerD"),
    ("IE", "Ireland",        "IE-Dublin",   "PartnerB"),
    ("GR", "Greece",         "GR-Attica",   "PartnerC"),
    ("RO", "Romania",        "RO-Bucuresti","PartnerE"),
    ("BG", "Bulgaria",       "BG-Sofia",    "PartnerE"),
    ("HR", "Croatia",        "HR-Zagreb",   "PartnerC"),
    ("SI", "Slovenia",       "SI-Osrednja", "PartnerC"),
]

# ---------------------------------------------------------------------------
# DIM_COUNTRY
# ---------------------------------------------------------------------------
country_rows = [
    {"country_code": c[0], "country_name": c[1], "region": c[2], "partner": c[3]}
    for c in COUNTRIES
]
pd.DataFrame(country_rows).to_csv(MASTER_DIR / "dim_country.csv", index=False)

# ---------------------------------------------------------------------------
# DIM_STORE — ~25 stores per country = ~575 stores
# ---------------------------------------------------------------------------
CITY_BY_COUNTRY = {
    "DE": ["Aschaffenburg", "Hanau", "Frankfurt", "Munich", "Berlin",
           "Hamburg", "Stuttgart", "Cologne", "Leipzig", "Dresden"],
    "FR": ["Paris", "Lyon", "Marseille", "Toulouse", "Lille", "Nantes",
           "Bordeaux", "Strasbourg", "Nice", "Rennes"],
    "IT": ["Milano", "Roma", "Napoli", "Torino", "Bologna", "Firenze",
           "Palermo", "Genova", "Verona", "Bari"],
    "ES": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao",
           "Malaga", "Zaragoza", "Murcia"],
    "NL": ["Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Eindhoven"],
    "BE": ["Brussels", "Antwerp", "Ghent", "Liege"],
    "AT": ["Vienna", "Graz", "Linz", "Salzburg"],
    "CH": ["Zurich", "Geneva", "Bern", "Basel"],
    "PL": ["Warsaw", "Krakow", "Wroclaw", "Poznan", "Gdansk"],
    "CZ": ["Prague", "Brno", "Ostrava"],
    "SK": ["Bratislava", "Kosice"],
    "HU": ["Budapest", "Debrecen", "Szeged"],
    "SE": ["Stockholm", "Gothenburg", "Malmo"],
    "DK": ["Copenhagen", "Aarhus", "Odense"],
    "NO": ["Oslo", "Bergen", "Trondheim"],
    "FI": ["Helsinki", "Espoo", "Tampere"],
    "PT": ["Lisbon", "Porto", "Coimbra"],
    "IE": ["Dublin", "Cork", "Galway"],
    "GR": ["Athens", "Thessaloniki"],
    "RO": ["Bucharest", "Cluj", "Timisoara"],
    "BG": ["Sofia", "Plovdiv"],
    "HR": ["Zagreb", "Split"],
    "SI": ["Ljubljana", "Maribor"],
}

CHANNELS = ["store", "outlet", "online"]
CHANNEL_WEIGHTS = [0.78, 0.12, 0.10]

store_rows = []
counter = 1
for iso, name, region, partner in COUNTRIES:
    cities = CITY_BY_COUNTRY.get(iso, [name])
    n_stores = 25
    for i in range(n_stores):
        city = random.choice(cities)
        suffix = f"{counter:04d}"
        # Canonical store id varies by country to mimic real heterogeneity
        if iso in {"DE", "AT", "CH"}:
            store_id = f"{iso}-{suffix}"
        elif iso == "FR":
            store_id = f"{iso}_{int(suffix):03d}"
        elif iso == "IT":
            store_id = f"{iso}/{int(suffix):03d}"
        else:
            store_id = f"{iso}-{suffix}"
        store_rows.append({
            "store_key": counter,
            "store_id_canon": store_id,
            "store_name": f"SPORT2000 {city}",
            "country": iso,
            "region": region,
            "partner": partner,
            "default_channel": random.choices(CHANNELS, CHANNEL_WEIGHTS)[0],
        })
        counter += 1

pd.DataFrame(store_rows).to_csv(MASTER_DIR / "dim_store.csv", index=False)

# ---------------------------------------------------------------------------
# DIM_PRODUCT — ~80 SKUs across realistic sport categories/brands
# ---------------------------------------------------------------------------
PRODUCTS = [
    # name,                  brand,             category,  rrp
    ("Air Zoom Pegasus",     "Nike",            "Running", 119.99),
    ("Pegasus Trail",        "Nike",            "Running", 139.99),
    ("React Infinity",       "Nike",            "Running", 149.99),
    ("Vaporfly Next",        "Nike",            "Running", 249.99),
    ("Dri-Fit Tee",          "Adidas",          "Training",  49.99),
    ("Ultraboost Light",     "Adidas",          "Running", 179.99),
    ("Adizero Adios",        "Adidas",          "Running", 159.99),
    ("Stan Smith",           "Adidas",          "Lifestyle", 99.99),
    ("Terrex Jacket",        "The North Face",  "Outdoor",  129.99),
    ("Nuptse Down Jacket",   "The North Face",  "Outdoor",  299.99),
    ("Vectiv Fastpack",      "The North Face",  "Outdoor",  159.99),
    ("Gel-Kayano",           "Asics",           "Running", 189.99),
    ("Gel-Nimbus",           "Asics",           "Running", 199.99),
    ("Novablast",            "Asics",           "Running", 139.99),
    ("Glycerin 21",          "Brooks",          "Running", 169.99),
    ("Ghost 16",             "Brooks",          "Running", 149.99),
    ("Clifton 9",            "Hoka",            "Running", 159.99),
    ("Bondi 8",              "Hoka",            "Running", 179.99),
    ("Speedgoat 5",          "Hoka",            "Outdoor", 149.99),
    ("Salomon Speedcross",   "Salomon",         "Outdoor", 144.99),
    ("Salomon XA Pro",       "Salomon",         "Outdoor", 169.99),
    ("Quest 4 GTX",          "Salomon",         "Outdoor", 199.99),
    ("MX Trainer",           "New Balance",     "Training",  99.99),
    ("Fresh Foam 1080",      "New Balance",     "Running", 169.99),
    ("574 Classic",          "New Balance",     "Lifestyle", 99.99),
    ("Old Skool",            "Vans",            "Lifestyle",  79.99),
    ("Sk8-Hi",               "Vans",            "Lifestyle",  89.99),
    ("Chuck Taylor",         "Converse",        "Lifestyle",  74.99),
    ("Rivalry Mid",          "Adidas",          "Lifestyle",  89.99),
    ("Air Force 1",          "Nike",            "Lifestyle", 119.99),
    ("Tech Fleece Hoodie",   "Nike",            "Training",  99.99),
    ("Essentials Hoodie",    "Adidas",          "Training",  59.99),
    ("Future Icons Pant",    "Adidas",          "Training",  64.99),
    ("Pro Dri-Fit Tights",   "Nike",            "Training",  44.99),
    ("Resolve Jacket",       "The North Face",  "Outdoor",  119.99),
    ("Borealis Backpack",    "The North Face",  "Outdoor",   99.99),
    ("Speedlite Vest",       "Salomon",         "Outdoor",   89.99),
    ("Eco Trail Pants",      "Salomon",         "Outdoor",   99.99),
    ("Goggle Sport",         "Oakley",          "Outdoor",  149.99),
    ("Holbrook Sunglasses",  "Oakley",          "Lifestyle", 129.99),
    ("Iconic Polo",          "Lacoste",         "Lifestyle",  99.99),
    ("Tracksuit Pro",        "Puma",            "Training",  69.99),
    ("Velocity Nitro",       "Puma",            "Running", 119.99),
    ("Suede Classic",        "Puma",            "Lifestyle",  79.99),
    ("Cell Endura",          "Puma",            "Lifestyle",  89.99),
    ("Wave Rider 27",        "Mizuno",          "Running", 149.99),
    ("Wave Sky 7",            "Mizuno",         "Running", 169.99),
    ("Mach 5",               "Hoka",            "Running", 139.99),
    ("Pegasus Premium",      "Nike",            "Running", 159.99),
    ("Solar Boost",          "Adidas",          "Running", 159.99),
    ("Endorphin Speed",      "Saucony",         "Running", 179.99),
    ("Triumph 21",           "Saucony",         "Running", 159.99),
    ("Kinvara 14",           "Saucony",         "Running", 119.99),
    ("Outdoor Beanie",       "The North Face",  "Outdoor",   34.99),
    ("Thermal Gloves",       "Salomon",         "Outdoor",   39.99),
    ("Cycling Jersey",       "Castelli",        "Cycling",   89.99),
    ("Cycling Bibshort",     "Castelli",        "Cycling",  129.99),
    ("Road Helmet Pro",      "Giro",            "Cycling",  149.99),
    ("MTB Helmet",           "Giro",            "Cycling",  179.99),
    ("Bike Gloves",          "Castelli",        "Cycling",   39.99),
    ("Yoga Mat Pro",         "Manduka",         "Fitness",   89.99),
    ("Yoga Block",           "Manduka",         "Fitness",   19.99),
    ("Resistance Set",       "TRX",             "Fitness",  149.99),
    ("Pull-Up Bar",          "Reebok",          "Fitness",   59.99),
    ("Boxing Gloves",        "Everlast",        "Fitness",   49.99),
    ("Tennis Racquet Pro",   "Wilson",          "Tennis",   199.99),
    ("Tennis Racquet Lite",  "Wilson",          "Tennis",   129.99),
    ("Tennis Balls 4x",      "Wilson",          "Tennis",    14.99),
    ("Padel Racquet",        "Head",            "Padel",    199.99),
    ("Padel Balls 3x",       "Head",            "Padel",     11.99),
    ("Football Pro Ball",    "Adidas",          "Football",  39.99),
    ("Football Boots Elite", "Nike",            "Football", 229.99),
    ("Football Boots Mid",   "Adidas",          "Football", 129.99),
    ("Shin Guards",          "Nike",            "Football",  24.99),
    ("Goalie Gloves",        "Adidas",          "Football",  59.99),
    ("Ski Helmet",           "Atomic",          "Ski",      149.99),
    ("Ski Goggles",          "Atomic",          "Ski",      109.99),
    ("Ski Jacket",           "Salomon",         "Ski",      299.99),
    ("Ski Pants",            "Salomon",         "Ski",      199.99),
    ("Trekking Pole",        "Black Diamond",   "Outdoor",   89.99),
    ("Headlamp",             "Petzl",           "Outdoor",   59.99),
]

product_rows = []
for i, (name, brand, cat, rrp) in enumerate(PRODUCTS, start=1):
    sku_digits = f"{77000 + i*131:05d}"
    product_rows.append({
        "product_key": i,
        "sku_canon": f"SKU-{sku_digits}",
        "product_name": name,
        "brand_canon": brand,
        "category_canon": cat,
        "rrp_eur": rrp,
        "valid_from": "2024-01-01",
        "valid_to": "2099-12-31",
    })

pd.DataFrame(product_rows).to_csv(MASTER_DIR / "dim_product.csv", index=False)

# ---------------------------------------------------------------------------
# DIM_CHANNEL
# ---------------------------------------------------------------------------
pd.DataFrame([
    {"channel_key": 1, "channel_code": "store",  "channel_name": "Brick & Mortar"},
    {"channel_key": 2, "channel_code": "outlet", "channel_name": "Outlet"},
    {"channel_key": 3, "channel_code": "online", "channel_name": "E-Commerce"},
]).to_csv(MASTER_DIR / "dim_channel.csv", index=False)

print(f"Wrote master data to {MASTER_DIR}")
print(f"  - {len(country_rows)} countries")
print(f"  - {len(store_rows)} stores")
print(f"  - {len(product_rows)} products")
