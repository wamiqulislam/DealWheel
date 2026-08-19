"""
src/features/numeric_features.py

Per-row numeric feature engineering that doesn't require comparing a
row to the rest of the dataset (that's market_features.py and
location_features.py). Covers:
    car_age, mileage_per_year, is_new_car, is_very_old,
    engine_size_category, mileage_category, mileage_ratio,
    is_high_mileage, is_low_mileage, log_mileage, log_engine_capacity,
    price_per_cc, mileage_density, (optionally) log_price

ASSUMPTION -- reference year for car_age:
The feature dictionary defines car_age as "current_year - year". A
single wall-clock "current year" is fine for a one-off run, but this
pipeline may reprocess listings scraped in different years, so using
each row's own scrape_date year is more correct when it's available
(a 2023-scraped listing's age is relative to 2023, not to whenever
you happen to re-run the pipeline). Rows without a usable scrape_date
fall back to settings.FALLBACK_CURRENT_YEAR. Set
FALLBACK_CURRENT_YEAR in .env if you always want literal wall-clock
current year behavior instead.

ASSUMPTION -- AVERAGE_KM_PER_YEAR (config/settings.py, default
12,000 km/year): used to compute the "expected" mileage for a car of
a given age. This number is a genuine assumption -- there's no
authoritative source for average annual mileage in Pakistan baked
into the data, so this is a reasonable default you can override via
.env.
"""

import numpy as np
import pandas as pd

from config.settings import (
    AVERAGE_KM_PER_YEAR,
    FALLBACK_CURRENT_YEAR,
    HIGH_MILEAGE_RATIO,
    LOW_MILEAGE_RATIO,
    NEW_CAR_MAX_AGE,
    VERY_OLD_MIN_AGE,
)

ENGINE_SIZE_BINS = [-1, 0, 800, 1000, 1300, 1600, 2000, 2500, 3000, np.inf]
ENGINE_SIZE_LABELS = [
    "Electric",
    "<=800cc",
    "801-1000cc",
    "1001-1300cc",
    "1301-1600cc",
    "1601-2000cc",
    "2001-2500cc",
    "2501-3000cc",
    "3000cc+",
]

MILEAGE_BINS = [-1, 20_000, 50_000, 100_000, 150_000, np.inf]
MILEAGE_LABELS = ["<20k", "20k-50k", "50k-100k", "100k-150k", "150k+"]


def _reference_year(df):
    """Per-row reference year: scrape_date's year if present/valid, else FALLBACK_CURRENT_YEAR."""
    if "scrape_date" in df.columns:
        scrape_year = pd.to_datetime(df["scrape_date"], errors="coerce").dt.year
        return scrape_year.fillna(FALLBACK_CURRENT_YEAR).astype(int)
    return pd.Series(FALLBACK_CURRENT_YEAR, index=df.index, dtype="int64")


def compute_numeric_features(df, verbose=True):
    df = df.copy()

    ref_year = _reference_year(df)
    df["car_age"] = (ref_year - df["year"]).clip(lower=0)

    denom_age = df["car_age"].clip(lower=1)
    df["mileage_per_year"] = df["mileage"] / denom_age

    df["is_new_car"] = df["car_age"] <= NEW_CAR_MAX_AGE
    df["is_very_old"] = df["car_age"] > VERY_OLD_MIN_AGE

    df["engine_size_category"] = pd.cut(
        df["engine_capacity"], bins=ENGINE_SIZE_BINS, labels=ENGINE_SIZE_LABELS
    ).astype(str)

    df["mileage_category"] = pd.cut(
        df["mileage"], bins=MILEAGE_BINS, labels=MILEAGE_LABELS
    ).astype(str)

    expected_mileage = denom_age * AVERAGE_KM_PER_YEAR
    df["mileage_ratio"] = df["mileage"] / expected_mileage.replace(0, np.nan)
    df["mileage_ratio"] = df["mileage_ratio"].fillna(0.0)

    df["is_high_mileage"] = df["mileage_ratio"] > HIGH_MILEAGE_RATIO
    df["is_low_mileage"] = df["mileage_ratio"] < LOW_MILEAGE_RATIO

    df["log_mileage"] = np.log1p(df["mileage"].clip(lower=0))
    df["log_engine_capacity"] = np.log1p(df["engine_capacity"].clip(lower=0))

    # Analysis-only: guard against divide-by-zero for electric listings
    # (engine_capacity == 0).
    safe_engine = df["engine_capacity"].replace(0, np.nan)
    df["price_per_cc"] = df["price"] / safe_engine
    df["mileage_density"] = df["mileage"] / safe_engine

    if verbose:
        print(
            f"[numeric] car_age avg={df['car_age'].mean():.1f}, "
            f"mileage_ratio avg={df['mileage_ratio'].mean():.2f}, "
            f"high_mileage={int(df['is_high_mileage'].sum()):,}, "
            f"low_mileage={int(df['is_low_mileage'].sum()):,}"
        )

    return df


def compute_log_price(df, verbose=True):
    """
    Experimental target column -- NOT called by build_features.py by
    default (the feature dictionary marks log_price "not stored
    unless experimenting"). Call this explicitly if you want it.
    """
    df = df.copy()
    df["log_price"] = np.log1p(df["price"].clip(lower=0))
    if verbose:
        print(f"[numeric] log_price computed for {len(df):,} rows")
    return df
