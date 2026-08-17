"""
null_handler.py

Handles missing / NULL values in the listings dataset:
    1. Electric cars with NULL engine_capacity -> set to 0
    2. Missing body_type -> filled using brand+model, else "Unknown"
    3. Missing is_featured -> set to False
    4. Any remaining rows with NULL values -> dropped

Each function returns the modified dataframe plus the counts needed
for the one-line summary printed by clean_nulls().
"""

import pandas as pd
import numpy as np


def fill_electric_engine_capacity(df):
    """Electric/EV/BEV listings with a NULL engine_capacity are set to 0."""
    electric_mask = (
        df["fuel_type"].astype(str).str.strip().str.upper().isin(["ELECTRIC", "EV", "BEV"])
    )
    target_mask = electric_mask & df["engine_capacity"].isna()
    count = int(target_mask.sum())

    df.loc[target_mask, "engine_capacity"] = 0
    return df, count


def fill_body_type(df):
    """
    Missing/"N/A" body_type is filled with the most common body_type
    for the same brand+model. If no known body_type exists for that
    brand+model, it's set to "Unknown".
    """
    missing_mask = (
        df["body_type"].isna()
        | df["body_type"].astype(str).str.strip().str.upper().eq("N/A")
    )

    known_body_types = (
        df.loc[~missing_mask]
        .groupby(["brand", "model"])["body_type"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan)
    )

    filled_count = 0
    unknown_count = 0

    for idx in df.index[missing_mask]:
        key = (df.at[idx, "brand"], df.at[idx, "model"])
        body_type = known_body_types.get(key, np.nan)

        if pd.notna(body_type):
            df.at[idx, "body_type"] = body_type
            filled_count += 1
        else:
            df.at[idx, "body_type"] = "Unknown"
            unknown_count += 1

    return df, filled_count, unknown_count


def fill_is_featured(df):
    """NULL is_featured -> False."""
    count = int(df["is_featured"].isna().sum())
    df["is_featured"] = df["is_featured"].fillna(False)
    return df, count


def drop_remaining_nulls(df):
    """Drop any row that still has a NULL value in any column."""
    rows_before = len(df)
    df = df.dropna()
    removed = rows_before - len(df)
    return df, removed


def clean_nulls(df, verbose=True):
    """
    Runs all null-handling steps in order.
    Prints a short (2-3 line) summary per step.
    """
    df, electric_filled = fill_electric_engine_capacity(df)
    if verbose:
        print(f"[nulls] engine_capacity: {electric_filled:,} electric listings set to 0")

    df, body_filled, body_unknown = fill_body_type(df)
    if verbose:
        print(f"[nulls] body_type: {body_filled:,} filled from brand+model, {body_unknown:,} set to 'Unknown'")

    df, featured_filled = fill_is_featured(df)
    if verbose:
        print(f"[nulls] is_featured: {featured_filled:,} NULLs set to False")

    df, rows_dropped = drop_remaining_nulls(df)
    if verbose:
        print(f"[nulls] dropped {rows_dropped:,} rows still containing NULLs -> {len(df):,} rows remain")

    return df
