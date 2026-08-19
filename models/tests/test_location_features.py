import pandas as pd

from location_features import compute_location_features


def make_df():
    return pd.DataFrame([
        {"city": "Lahore", "price": 4000000},
        {"city": "Lahore", "price": 5000000},
        {"city": "Jhang", "price": 1000000},
    ])


def test_is_large_city():
    df = compute_location_features(make_df(), verbose=False)
    lahore_rows = df[df["city"] == "Lahore"]
    jhang_rows = df[df["city"] == "Jhang"]
    assert (lahore_rows["is_large_city"] == True).all()  # noqa: E712
    assert (jhang_rows["is_large_city"] == False).all()  # noqa: E712


def test_city_avg_price_and_listing_count():
    df = compute_location_features(make_df(), verbose=False)
    lahore_rows = df[df["city"] == "Lahore"]
    assert (lahore_rows["city_avg_price"] == 4500000).all()
    assert (lahore_rows["city_listing_count"] == 2).all()

    jhang_row = df[df["city"] == "Jhang"].iloc[0]
    assert jhang_row["city_avg_price"] == 1000000
    assert jhang_row["city_listing_count"] == 1


def test_is_large_city_depends_on_already_cleaned_city_values():
    # lowercase "lahore" is NOT in LARGE_CITIES -- text_cleaning.py
    # must run before this module for is_large_city to be correct.
    df = pd.DataFrame([{"city": "lahore", "price": 1000000}])
    result = compute_location_features(df, verbose=False)
    assert bool(result.loc[0, "is_large_city"]) is False
