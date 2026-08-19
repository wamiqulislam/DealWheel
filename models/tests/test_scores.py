import pandas as pd

from config.column_manifest import FEAT_COLUMNS, SELLER_FLAG_COLUMNS
from scores import compute_all_scores


def make_feat_df(true_features=()):
    row = {c: (c in true_features) for c in FEAT_COLUMNS}
    for c in SELLER_FLAG_COLUMNS:
        row[c] = False
    return pd.DataFrame([row])


def test_equipment_score_sums_all_feat_columns():
    df = make_feat_df(true_features=["feat_abs", "feat_air_bags", "feat_alloy_wheels"])
    result = compute_all_scores(df, verbose=False)
    assert result.loc[0, "equipment_score"] == 3


def test_equipment_score_zero_when_nothing_set():
    df = make_feat_df(true_features=[])
    result = compute_all_scores(df, verbose=False)
    assert result.loc[0, "equipment_score"] == 0


def test_safety_score_only_counts_safety_features():
    df = make_feat_df(true_features=["feat_abs", "feat_air_bags", "feat_power_locks"])
    result = compute_all_scores(df, verbose=False)
    # feat_power_locks is a comfort feature, not safety
    assert result.loc[0, "safety_score"] == 2


def test_a_feature_can_count_toward_multiple_categories():
    # feat_head_up_display_hud is intentionally both luxury and technology
    df = make_feat_df(true_features=["feat_head_up_display_hud"])
    result = compute_all_scores(df, verbose=False)
    assert result.loc[0, "luxury_score"] == 1
    assert result.loc[0, "technology_score"] == 1
    # but equipment_score only counts it once
    assert result.loc[0, "equipment_score"] == 1


def test_seller_confidence_and_risk_scores():
    df = make_feat_df(true_features=[])
    df["seller_genuine_condition"] = True
    df["seller_service_history"] = True
    df["seller_minor_accident"] = True
    result = compute_all_scores(df, verbose=False)
    assert result.loc[0, "seller_confidence_score"] == 2
    assert result.loc[0, "seller_risk_score"] == 1
    assert result.loc[0, "seller_urgency_score"] == 0


def test_missing_seller_columns_do_not_crash():
    # scores.py should be safe to call even before seller_keywords.py has run
    df = make_feat_df(true_features=["feat_abs"])
    for c in SELLER_FLAG_COLUMNS:
        del df[c]
    result = compute_all_scores(df, verbose=False)
    assert result.loc[0, "seller_confidence_score"] == 0
    assert result.loc[0, "equipment_score"] == 1
