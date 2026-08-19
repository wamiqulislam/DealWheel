"""
tests/test_pipeline_integration.py

Runs the full preprocessing + feature-engineering pipeline against
the bundled synthetic dataset (data/raw/sample_listings.csv) and
checks the output has the right shape and a handful of known-correct
values -- a coarse end-to-end smoke test on top of the focused
per-module tests in the other test files.
"""

from pathlib import Path

import pandas as pd
import pytest

from config.column_manifest import PROCESSED_LISTINGS_COLUMNS
from clean import clean_dataframe  # src/preprocessing/clean.py
from build_features import build_features, select_processed_columns

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_listings.csv"


@pytest.fixture(scope="module")
def processed():
    raw = pd.read_csv(SAMPLE_CSV)
    raw = raw.rename(columns={"id": "source_pk"})

    cleaned = clean_dataframe(raw, verbose=False)
    cleaned = cleaned.copy()
    cleaned["color"] = cleaned["color_clean"]
    cleaned = cleaned.drop(columns=["color_clean"])

    featured = build_features(cleaned, verbose=False)
    featured["listing_id"] = featured["source_pk"]
    return select_processed_columns(featured, include_listing_id=True)


def test_output_has_exact_schema_columns(processed):
    assert set(processed.columns) == set(PROCESSED_LISTINGS_COLUMNS)


def test_bad_rows_were_removed(processed):
    # sample CSV has 18 rows: 1 exact duplicate + 4 impossible-value
    # rows (bad price/year/mileage/engine) + 1 row with a genuinely
    # missing required field should all be gone.
    assert len(processed) == 12


def test_no_nulls_in_boolean_flag_columns(processed):
    flag_columns = [c for c in processed.columns if c.startswith(("seller_", "contains_", "is_", "feat_"))]
    for col in flag_columns:
        assert processed[col].isna().sum() == 0, col


def test_known_row_seller_flags(processed):
    row = processed[processed["listing_id"] == 1].iloc[0]
    assert bool(row["seller_genuine_condition"]) is True
    assert bool(row["seller_original_book"]) is True
    assert bool(row["seller_minor_accident"]) is False


def test_known_row_market_segment(processed):
    corolla_rows = processed[(processed["brand"] == "Toyota") & (processed["model"] == "Corolla GLi")]
    assert len(corolla_rows) == 2
    assert (corolla_rows["market_listing_count"] == 2).all()
    assert corolla_rows["market_avg_price"].iloc[0] == corolla_rows["market_avg_price"].iloc[1]


def test_price_and_analysis_columns_present_but_not_trainable(processed):
    from config.column_manifest import TRAINING_FEATURES

    assert "market_avg_price" in processed.columns
    assert "market_avg_price" not in TRAINING_FEATURES
