"""
src/features/build_features.py

Runs the full "part 2" pipeline (feature engineering) on an already-
cleaned dataframe (i.e. the output of src/preprocessing/main.py):

    1. text_cleaning      - standardize text/categorical columns
    2. seller_keywords    - seller_* flags from quick-comment buttons
    3. content_flags      - contains_* flags from free text
    4. scores              - equipment/safety/comfort/luxury/tech +
                              seller_confidence/risk/urgency scores
    5. numeric_features    - car_age, mileage/engine derived features
    6. market_features     - brand+model+year comparisons
    7. location_features   - city-level comparisons

The order matters:
    - scores needs the seller_* flags (step 2) to already exist.
    - market_features needs equipment_score (step 4) to already exist.
    - location_features needs `city` already standardized (step 1).

Call build_features(df) to run all seven steps. Call
select_processed_columns(df) afterwards to get exactly the columns
cars.processed_listings expects, in schema order (everything except
`id` and `listing_id`, which the pipeline layer adds -- see
src/db/database.py for why listing_id needs special handling).
"""

import numpy as np

from config.column_manifest import PROCESSED_LISTINGS_COLUMNS
from text_cleaning import clean_text_columns
from seller_keywords import extract_seller_flags
from content_flags import extract_contains_flags
from scores import compute_all_scores
from numeric_features import compute_numeric_features, compute_log_price
from market_features import compute_market_features
from location_features import compute_location_features


def build_features(df, verbose=True, include_log_price=False):
    """
    Runs the full feature-engineering stage and returns the enriched
    dataframe. log_price is the schema's one "experimental, nullable,
    not stored unless experimenting" column -- it's written as NULL
    by default; pass include_log_price=True to actually compute it.
    """
    if verbose:
        print(f"[features] starting feature engineering on {len(df):,} rows")

    df = clean_text_columns(df, verbose=verbose)
    df = extract_seller_flags(df, verbose=verbose)
    df = extract_contains_flags(df, verbose=verbose)
    df = compute_all_scores(df, verbose=verbose)
    df = compute_numeric_features(df, verbose=verbose)
    df = compute_market_features(df, verbose=verbose)
    df = compute_location_features(df, verbose=verbose)

    if include_log_price:
        df = compute_log_price(df, verbose=verbose)
    elif "log_price" not in df.columns:
        df["log_price"] = np.nan

    if verbose:
        print(f"[features] done -- {len(df):,} rows, {df.shape[1]:,} columns")

    return df


def select_processed_columns(df, include_listing_id=False):
    """
    Returns df restricted to exactly the cars.processed_listings
    columns (schema order). Set include_listing_id=True if the
    caller has already attached a `listing_id` column mapped from
    listings.id (see src/db/database.py).
    """
    columns = list(PROCESSED_LISTINGS_COLUMNS)
    if not include_listing_id:
        columns = [c for c in columns if c != "listing_id"]

    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"select_processed_columns: missing expected columns: {missing}")

    return df[columns].copy()
