import pandas as pd
import pytest

from market_features import compute_market_features


def make_df():
    return pd.DataFrame([
        {"brand": "Toyota", "model": "Corolla", "year": 2021, "price": 4000000, "mileage": 20000, "equipment_score": 6},
        {"brand": "Toyota", "model": "Corolla", "year": 2021, "price": 4200000, "mileage": 30000, "equipment_score": 4},
        {"brand": "Honda", "model": "Civic", "year": 2019, "price": 5000000, "mileage": 60000, "equipment_score": 5},
    ])


def test_market_avg_price_and_listing_count():
    df = compute_market_features(make_df(), verbose=False)
    corolla = df[df["model"] == "Corolla"]
    assert (corolla["market_avg_price"] == 4100000).all()
    assert (corolla["market_listing_count"] == 2).all()

    civic = df[df["model"] == "Civic"]
    assert civic["market_listing_count"].iloc[0] == 1
    assert pd.isna(civic["market_std_price"].iloc[0])  # single-row segment -> NaN std


def test_market_price_difference_and_ratio():
    df = compute_market_features(make_df(), verbose=False)
    row = df[df["price"] == 4000000].iloc[0]
    assert row["market_price_difference"] == pytest.approx(-100000)
    assert row["market_price_ratio"] == pytest.approx(4000000 / 4100000)


def test_better_equipped_than_average():
    df = compute_market_features(make_df(), verbose=False)
    corolla = df[df["model"] == "Corolla"].sort_values("equipment_score", ascending=False)
    assert bool(corolla.iloc[0]["better_equipped_than_average"]) is True   # 6 > avg 5
    assert bool(corolla.iloc[1]["better_equipped_than_average"]) is False  # 4 < avg 5


def test_mileage_difference():
    df = compute_market_features(make_df(), verbose=False)
    corolla = df[df["model"] == "Corolla"]
    assert corolla["market_avg_mileage"].iloc[0] == 25000
    lower_mileage_row = corolla[corolla["mileage"] == 20000].iloc[0]
    assert lower_mileage_row["mileage_difference"] == -5000


def test_requires_equipment_score():
    df = make_df().drop(columns=["equipment_score"])
    with pytest.raises(ValueError):
        compute_market_features(df, verbose=False)
