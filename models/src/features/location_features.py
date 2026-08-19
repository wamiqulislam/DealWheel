"""
src/features/location_features.py

City-level features: is_large_city (lookup, see location_maps.py),
city_avg_price and city_listing_count (aggregates over the cleaned
`city` column). Should run after text_cleaning.py so city values are
already standardized (otherwise "Lahore" and "lahore " would form two
separate groups).
"""

from location_maps import LARGE_CITIES


def compute_location_features(df, verbose=True):
    df = df.copy()

    df["is_large_city"] = df["city"].isin(LARGE_CITIES)

    city_group = df.groupby("city")["price"]
    df["city_avg_price"] = city_group.transform("mean")
    df["city_listing_count"] = city_group.transform("count")

    if verbose:
        large_city_count = int(df["is_large_city"].sum())
        print(
            f"[location] {large_city_count:,}/{len(df):,} rows in a large city, "
            f"{df['city'].nunique():,} distinct cities"
        )

    return df
