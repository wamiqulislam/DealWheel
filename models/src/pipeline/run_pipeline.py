"""
src/pipeline/run_pipeline.py

The "glue everything together" script:

    cars.listings (or a CSV)
        -> src/preprocessing  (nulls, color, duplicates/impossibles)
        -> src/features       (text cleaning, keyword search, scores,
                                numeric/market/location features)
        -> cars.processed_listings (or a CSV)

Usage
-----
Run against the database (reads config/.env for connection settings):
    python -m src.pipeline.run_pipeline --source db --write db

Run against local CSV files, no database needed (useful for testing,
and for the bundled sample dataset):
    python -m src.pipeline.run_pipeline \\
        --source csv --input data/raw/sample_listings.csv \\
        --write csv --output data/processed/processed_listings_sample.csv

Mix and match source/destination freely, e.g. pull from the database
but write a CSV for inspection before touching processed_listings:
    python -m src.pipeline.run_pipeline --source db --write csv --output data/processed/preview.csv

Run `python -m src.pipeline.run_pipeline --help` for all options.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PREPROCESSING_DIR = SRC_DIR / "preprocessing"
FEATURES_DIR = SRC_DIR / "features"

# --------------------------------------------------------------
# src/preprocessing and src/features use plain sibling imports
# internally (e.g. `from null_handler import clean_nulls`,
# `from text_cleaning import clean_text_columns`) rather than
# package-qualified ones. That keeps the already-working
# preprocessing modules untouched, but it means both directories
# need to be on sys.path -- alongside the project root itself, for
# the `config.*` imports used throughout src/features. This is the
# one place that wiring lives; every other module just does normal
# imports assuming this has already run.
# --------------------------------------------------------------
for path in (PROJECT_ROOT, SRC_DIR, PREPROCESSING_DIR, FEATURES_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from config.settings import DB_SCHEMA  # noqa: E402
from main import clean_dataframe  # noqa: E402  (src/preprocessing/main.py)
from build_features import build_features, select_processed_columns  # noqa: E402


def load_from_csv(input_csv):
    df = pd.read_csv(input_csv)
    print(f"[pipeline] loaded {len(df):,} rows from {input_csv}")
    return df


def load_from_db(limit=None):
    from db.database import get_engine, read_listings  # local import: only needed for db mode

    engine = get_engine()
    try:
        return read_listings(engine, limit=limit)
    finally:
        engine.dispose()


def attach_source_pk(df):
    """
    Ensures df has a `source_pk` column (listings.id) to later become
    processed_listings.listing_id. read_listings() (db mode) already
    provides this. For CSV mode, fall back to a raw `id` column if
    present, and otherwise to `listing_id` with a loud warning, since
    a CSV export might only have the external listing_id available.
    """
    if "source_pk" in df.columns:
        return df

    df = df.copy()
    if "id" in df.columns:
        df["source_pk"] = df["id"]
        return df

    if "listing_id" in df.columns:
        print(
            "[pipeline] WARNING: no `id`/`source_pk` column found -- falling back to "
            "`listing_id` (the external ad ID) as processed_listings.listing_id. "
            "This is only correct if you're intentionally using it as the row key; "
            "the real schema expects listings.id here. See src/db/database.py."
        )
        df["source_pk"] = df["listing_id"]
        return df

    raise ValueError("Input data has no `id`, `source_pk`, or `listing_id` column to key rows by.")


def fix_color_column(df):
    """
    color_cleaner.py (src/preprocessing) adds `color_clean` alongside
    the original `color`. cars.processed_listings only has one
    `color` column, so replace the raw value with the cleaned one
    here rather than editing color_cleaner.py itself.
    """
    df = df.copy()
    if "color_clean" in df.columns:
        df["color"] = df["color_clean"]
        df = df.drop(columns=["color_clean"])
    return df


def run(source="db", input_csv=None, write="db", output_csv=None, write_mode="replace", limit=None, include_log_price=False):
    # ---- load ----
    if source == "csv":
        if not input_csv:
            raise ValueError("--input is required when --source csv")
        df = load_from_csv(input_csv)
    elif source == "db":
        df = load_from_db(limit=limit)
    else:
        raise ValueError(f"Unknown source: {source!r}")

    df = attach_source_pk(df)

    # ---- clean ----
    df = clean_dataframe(df, verbose=True)
    df = fix_color_column(df)

    # ---- feature engineer ----
    df = build_features(df, verbose=True, include_log_price=include_log_price)

    # ---- assemble final frame ----
    df["listing_id"] = df["source_pk"]
    processed = select_processed_columns(df, include_listing_id=True)

    # ---- write ----
    if write in ("db", "both"):
        from db.database import get_engine, write_processed_listings

        engine = get_engine()
        try:
            write_processed_listings(processed, engine, schema=DB_SCHEMA, mode=write_mode)
        finally:
            engine.dispose()

    if write in ("csv", "both"):
        if not output_csv:
            raise ValueError("--output is required when --write csv (or both)")
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        processed.to_csv(output_csv, index=False)
        print(f"[pipeline] wrote {len(processed):,} rows to {output_csv}")

    print(f"[pipeline] done -- {len(processed):,} rows, {processed.shape[1]:,} columns")
    return processed


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["db", "csv"], default="db", help="Where to read raw listings from.")
    parser.add_argument("--input", help="Input CSV path (required if --source csv).")
    parser.add_argument("--write", choices=["db", "csv", "both"], default="db", help="Where to write processed_listings.")
    parser.add_argument("--output", help="Output CSV path (required if --write csv or both).")
    parser.add_argument(
        "--write-mode",
        choices=["replace", "append", "upsert"],
        default="replace",
        help="DB write mode (ignored for --write csv). 'replace' truncates + rebuilds the table (default, always safe to re-run).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only read this many rows from cars.listings (db mode, for quick testing).")
    parser.add_argument(
        "--include-log-price",
        action="store_true",
        help="Also compute the experimental log_price column (off by default, per the feature dictionary).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        source=args.source,
        input_csv=args.input,
        write=args.write,
        output_csv=args.output,
        write_mode=args.write_mode,
        limit=args.limit,
        include_log_price=args.include_log_price,
    )
