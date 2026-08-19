from config.column_manifest import (
    PROCESSED_LISTINGS_COLUMNS,
    RAW_LISTINGS_COLUMNS,
    FEAT_COLUMNS,
    TRAINING_FEATURES,
    ANALYSIS_ONLY_COLUMNS,
    TARGET_COLUMN,
    assert_no_duplicates,
)


def test_no_duplicate_columns():
    assert_no_duplicates()


def test_feat_columns_count():
    # 35 feat_* equipment flags scraped directly from listings.
    assert len(FEAT_COLUMNS) == 35
    assert all(c.startswith("feat_") for c in FEAT_COLUMNS)


def test_training_and_analysis_are_disjoint():
    overlap = set(TRAINING_FEATURES) & set(ANALYSIS_ONLY_COLUMNS)
    assert not overlap, f"Columns marked both trainable and analysis-only: {overlap}"


def test_target_not_in_training_features():
    assert TARGET_COLUMN not in TRAINING_FEATURES


def test_leakage_risk_columns_excluded_from_training():
    leakage_columns = [
        "market_avg_price",
        "market_median_price",
        "market_std_price",
        "market_price_difference",
        "market_price_ratio",
        "percent_below_market",
    ]
    for col in leakage_columns:
        assert col in ANALYSIS_ONLY_COLUMNS, f"{col} should be analysis-only (target leakage risk)"
        assert col not in TRAINING_FEATURES, f"{col} must never be used as a training feature"


def test_processed_columns_cover_training_and_target_and_analysis():
    expected = set(TRAINING_FEATURES) | {TARGET_COLUMN} | set(ANALYSIS_ONLY_COLUMNS) | {"listing_id"}
    assert set(PROCESSED_LISTINGS_COLUMNS) == expected


def test_raw_listings_has_expected_shape(raw_columns):
    assert len(raw_columns) == 56
    assert "id" in raw_columns
    assert "listing_id" in raw_columns
