"""
src/features/market_features.py

Compares each listing to others of the same brand + model + year
("market segment"). Must run AFTER scores.py, since
market_avg_equipment_score needs equipment_score to already exist.

IMPORTANT -- target leakage:
market_avg_price, market_median_price, market_std_price,
market_price_difference, market_price_ratio, and
percent_below_market are all derived from price (an aggregate of the
row's own market-segment prices, which necessarily includes the
row's own price). They're computed and stored here because the
schema calls for them ("Analysis Only" in the feature dictionary),
but config.column_manifest.ANALYSIS_ONLY_COLUMNS deliberately
excludes them from TRAINING_FEATURES. Do not add them to a model's
feature set later.

market_avg_mileage, mileage_difference, market_avg_equipment_score
and better_equipped_than_average do NOT use price, so they stay in
TRAINING_FEATURES.
"""

import numpy as np


MARKET_GROUP_COLUMNS = ["brand", "model", "year"]


def compute_market_features(df, verbose=True):
    df = df.copy()
    group = df.groupby(MARKET_GROUP_COLUMNS)

    # --- price-derived (analysis only / leakage risk) ---
    df["market_avg_price"] = group["price"].transform("mean")
    df["market_median_price"] = group["price"].transform("median")
    df["market_std_price"] = group["price"].transform("std")
    df["market_listing_count"] = group["price"].transform("count")

    safe_avg_price = df["market_avg_price"].replace(0, np.nan)
    df["market_price_difference"] = df["price"] - df["market_avg_price"]
    df["market_price_ratio"] = df["price"] / safe_avg_price
    df["percent_below_market"] = (df["market_avg_price"] - df["price"]) / safe_avg_price * 100

    # --- mileage/equipment comparisons (safe to train on) ---
    df["market_avg_mileage"] = group["mileage"].transform("mean")
    df["mileage_difference"] = df["mileage"] - df["market_avg_mileage"]

    if "equipment_score" not in df.columns:
        raise ValueError(
            "market_features.compute_market_features requires equipment_score to "
            "already exist -- run scores.compute_equipment_scores() first."
        )
    df["market_avg_equipment_score"] = group["equipment_score"].transform("mean")
    df["better_equipped_than_average"] = df["equipment_score"] > df["market_avg_equipment_score"]

    if verbose:
        singleton_segments = int((df["market_listing_count"] == 1).sum())
        print(
            f"[market] {df[MARKET_GROUP_COLUMNS].drop_duplicates().shape[0]:,} distinct "
            f"brand+model+year segments, {singleton_segments:,} rows in a segment of size 1 "
            f"(market_std_price will be NaN for those)"
        )

    return df
