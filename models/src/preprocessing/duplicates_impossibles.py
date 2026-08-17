"""
duplicates_impossibles.py

    1. Removes duplicate listings (by listing_id)
    2. Removes rows with impossible numeric values:
         - price   <= 0 or NULL
         - year    < 1950 or > 2027, or NULL
         - mileage < 0 or NULL
         - engine_capacity < 0 or NULL
"""

import pandas as pd

NUMERIC_COLUMNS = ["listing_id", "year", "mileage", "engine_capacity", "price"]

MIN_YEAR = 1950
MAX_YEAR = 2027


def remove_duplicate_listings(df):
    dup_mask = df["listing_id"].duplicated(keep="first")
    count = int(dup_mask.sum())
    df = df.loc[~dup_mask].copy()
    return df, count


def remove_impossible_values(df):
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    invalid_price = df["price"].isna() | (df["price"] <= 0)
    invalid_year = df["year"].isna() | (df["year"] < MIN_YEAR) | (df["year"] > MAX_YEAR)
    invalid_mileage = df["mileage"].isna() | (df["mileage"] < 0)
    invalid_engine = df["engine_capacity"].isna() | (df["engine_capacity"] < 0)

    invalid_mask = invalid_price | invalid_year | invalid_mileage | invalid_engine
    count = int(invalid_mask.sum())

    breakdown = {
        "price": int(invalid_price.sum()),
        "year": int(invalid_year.sum()),
        "mileage": int(invalid_mileage.sum()),
        "engine_capacity": int(invalid_engine.sum()),
    }

    df = df.loc[~invalid_mask].copy()
    return df, count, breakdown


def clean_duplicates_and_impossibles(df, verbose=True):
    """Runs both steps in order, printing a short summary per step."""
    df, dup_count = remove_duplicate_listings(df)
    if verbose:
        print(f"[dedupe] {dup_count:,} duplicate listings removed -> {len(df):,} rows remain")

    df, invalid_count, breakdown = remove_impossible_values(df)
    if verbose:
        print(
            f"[impossible values] {invalid_count:,} rows removed "
            f"(price={breakdown['price']}, year={breakdown['year']}, "
            f"mileage={breakdown['mileage']}, engine={breakdown['engine_capacity']}) "
            f"-> {len(df):,} rows remain"
        )

    return df
