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


def run_pipeline(input_csv="listings.csv", output_csv="listings_cleaned.csv"):
    df = pd.read_csv(input_csv)
    initial_rows = len(df)
    print(f"Loaded {initial_rows:,} rows from {input_csv}")

    df = clean_nulls(df)
    df = clean_color_column(df, column="color")
    df = clean_duplicates_and_impossibles(df)

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
