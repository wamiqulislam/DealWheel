"""
main.py

Runs the full "part 1" cleaning pipeline on the raw listings CSV:
    1. Null handling      (null_handler.py)
    2. Color cleaning     (color_cleaner.py)
    3. Duplicates & impossible numeric values (duplicates_impossibles.py)

Usage:
    python main.py [input_csv] [output_csv]

Defaults:
    input_csv  = listings.csv
    output_csv = listings_cleaned.csv

This is only the cleaning stage. Text extraction, feature engineering,
and the final "glue everything together" pipeline are separate,
later pieces of work and are NOT part of this script.
"""

import sys

import pandas as pd

from null_handler import clean_nulls
from color_cleaner import clean_color_column
from duplicates_impossibles import clean_duplicates_and_impossibles


def clean_dataframe(df, verbose=True):
    """
    Runs the three cleaning steps on an in-memory dataframe and
    returns the cleaned dataframe. This is the reusable piece: no CSV
    I/O, so it's also called directly by src/pipeline/run_pipeline.py
    when the source/destination is a database rather than a file.
    """
    initial_rows = len(df)
    if verbose:
        print(f"[preprocessing] starting from {initial_rows:,} rows")

    df = df.copy()

    # --- Defensive safety net (confirmed harmless, not fixing an
    #     active bug in the current dataset) ---
    # null_handler.drop_remaining_nulls() (last step of clean_nulls,
    # below) does a blanket df.dropna() across EVERY column. That's
    # correct for columns where a NULL genuinely makes the row
    # unusable (price, year, brand, model, ...). For description and
    # seller_comments specifically, the data has no NULLs in
    # practice, so this is a no-op for them today -- but a NULL raw
    # `color` is expected: color_cleaner.py's own "garbage value"
    # handling already turns that into color_clean="Unknown" a few
    # lines below, and title/ad_url are non-feature metadata that
    # shouldn't gate a row's usability either way. Filling these five
    # specific columns here (and ONLY these -- everything
    # null_handler.py has dedicated logic for, like engine_capacity,
    # body_type, is_featured, is left completely untouched, since
    # that logic depends on seeing real NaNs) means a future NULL in
    # any of them can't silently zero out feature-engineering rows,
    # and lets color_clean's "Unknown" fallback actually reach the
    # final row instead of the row being dropped first.
    optional_freetext_columns = ["title", "description", "seller_comments", "ad_url", "color"]
    for column in optional_freetext_columns:
        if column in df.columns:
            df[column] = df[column].fillna("")

    df = clean_nulls(df)
    df = clean_color_column(df, column="color")
    df = clean_duplicates_and_impossibles(df)

    if verbose:
        final_rows = len(df)
        removed_pct = (initial_rows - final_rows) / initial_rows * 100 if initial_rows else 0
        print(
            f"[preprocessing] {initial_rows:,} -> {final_rows:,} rows "
            f"({removed_pct:.2f}% removed)"
        )

    return df


def run_pipeline(input_csv="listings.csv", output_csv="listings_cleaned.csv"):
    """CSV-in, CSV-out CLI entry point. Thin wrapper around clean_dataframe()."""
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df):,} rows from {input_csv}")

    initial_rows = len(df)
    df = clean_dataframe(df, verbose=True)

    df.to_csv(output_csv, index=False)

    final_rows = len(df)
    removed_pct = (initial_rows - final_rows) / initial_rows * 100 if initial_rows else 0
    print(
        f"Done: {initial_rows:,} -> {final_rows:,} rows "
        f"({removed_pct:.2f}% removed). Saved to {output_csv}"
    )

    return df


if __name__ == "__main__":
    in_path = sys.argv[1] if len(sys.argv) > 1 else "listings.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "listings_cleaned.csv"
    run_pipeline(in_path, out_path)
