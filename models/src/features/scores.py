"""
src/features/scores.py

Rolls the boolean feat_* and seller_* flags up into composite integer
scores. Must run AFTER the feat_* columns exist (already true, since
they come straight from cars.listings) and AFTER seller_keywords.py
has added the seller_* flags.
"""

import pandas as pd

from config.column_manifest import FEAT_COLUMNS, SELLER_FLAG_COLUMNS
from feature_groups import (
    SAFETY_FEATURES,
    COMFORT_FEATURES,
    LUXURY_FEATURES,
    TECHNOLOGY_FEATURES,
    SELLER_POSITIVE_FLAGS,
    SELLER_NEGATIVE_FLAGS,
    SELLER_URGENCY_FLAGS,
)


def _sum_bool_columns(df, columns):
    """Sums the given boolean columns row-wise, treating missing/NaN as False."""
    present = [c for c in columns if c in df.columns]
    if not present:
        return pd.Series(0, index=df.index, dtype="int64")
    return df[present].fillna(False).astype(int).sum(axis=1)


def compute_equipment_scores(df, verbose=True):
    """Adds equipment_score, safety_score, comfort_score, luxury_score, technology_score."""
    df = df.copy()

    df["equipment_score"] = _sum_bool_columns(df, FEAT_COLUMNS)
    df["safety_score"] = _sum_bool_columns(df, SAFETY_FEATURES)
    df["comfort_score"] = _sum_bool_columns(df, COMFORT_FEATURES)
    df["luxury_score"] = _sum_bool_columns(df, LUXURY_FEATURES)
    df["technology_score"] = _sum_bool_columns(df, TECHNOLOGY_FEATURES)

    if verbose:
        print(
            f"[scores] equipment_score avg={df['equipment_score'].mean():.1f}/{len(FEAT_COLUMNS)}, "
            f"safety avg={df['safety_score'].mean():.1f}, comfort avg={df['comfort_score'].mean():.1f}, "
            f"luxury avg={df['luxury_score'].mean():.1f}, tech avg={df['technology_score'].mean():.1f}"
        )

    return df


def compute_seller_scores(df, verbose=True):
    """Adds seller_confidence_score, seller_risk_score, seller_urgency_score."""
    df = df.copy()

    df["seller_confidence_score"] = _sum_bool_columns(df, SELLER_POSITIVE_FLAGS)
    df["seller_risk_score"] = _sum_bool_columns(df, SELLER_NEGATIVE_FLAGS)
    df["seller_urgency_score"] = _sum_bool_columns(df, SELLER_URGENCY_FLAGS)

    if verbose:
        print(
            f"[scores] seller_confidence avg={df['seller_confidence_score'].mean():.2f}, "
            f"seller_risk avg={df['seller_risk_score'].mean():.2f}, "
            f"seller_urgency avg={df['seller_urgency_score'].mean():.2f}"
        )

    return df


def compute_all_scores(df, verbose=True):
    df = compute_equipment_scores(df, verbose=verbose)
    df = compute_seller_scores(df, verbose=verbose)
    return df
