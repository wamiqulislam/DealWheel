import math

import numpy as np
import pandas as pd

from numeric_features import compute_numeric_features, compute_log_price


def approx(value, tol=1e-6):
    return lambda other: math.isclose(other, value, abs_tol=tol)


def make_df(**overrides):
    base = dict(
        year=2021, mileage=25000, engine_capacity=1300, price=4000000,
        scrape_date="2026-01-01",
    )
    base.update(overrides)
    return pd.DataFrame([base])


def test_car_age_uses_scrape_date_year():
    df = compute_numeric_features(make_df(year=2021, scrape_date="2024-06-01"), verbose=False)
    assert df.loc[0, "car_age"] == 3  # 2024 - 2021


def test_car_age_never_negative():
    df = compute_numeric_features(make_df(year=2030, scrape_date="2024-01-01"), verbose=False)
    assert df.loc[0, "car_age"] == 0


def test_is_new_car_and_is_very_old():
    new_car = compute_numeric_features(make_df(year=2024, scrape_date="2025-01-01"), verbose=False)
    assert bool(new_car.loc[0, "is_new_car"]) is True
    assert bool(new_car.loc[0, "is_very_old"]) is False

    old_car = compute_numeric_features(make_df(year=2000, scrape_date="2026-01-01"), verbose=False)
    assert bool(old_car.loc[0, "is_new_car"]) is False
    assert bool(old_car.loc[0, "is_very_old"]) is True  # 26 years > 15


def test_engine_size_category_buckets():
    cases = {
        0: "Electric",
        660: "<=800cc",
        900: "801-1000cc",
        1300: "1001-1300cc",
        1800: "1601-2000cc",
        3500: "3000cc+",
    }
    for capacity, expected in cases.items():
        df = compute_numeric_features(make_df(engine_capacity=capacity), verbose=False)
        assert df.loc[0, "engine_size_category"] == expected, capacity


def test_mileage_category_buckets():
    cases = {5000: "<20k", 30000: "20k-50k", 75000: "50k-100k", 120000: "100k-150k", 200000: "150k+"}
    for mileage, expected in cases.items():
        df = compute_numeric_features(make_df(mileage=mileage), verbose=False)
        assert df.loc[0, "mileage_category"] == expected, mileage


def test_mileage_ratio_and_high_low_flags():
    # car_age=5 (2026-2021), AVERAGE_KM_PER_YEAR default 12000 -> expected=60000
    df = compute_numeric_features(make_df(mileage=90000, scrape_date="2026-01-01"), verbose=False)
    assert math.isclose(df.loc[0, "mileage_ratio"], 90000 / 60000, abs_tol=1e-6)
    assert bool(df.loc[0, "is_high_mileage"]) is True
    assert bool(df.loc[0, "is_low_mileage"]) is False


def test_price_per_cc_guards_electric_division_by_zero():
    df = compute_numeric_features(make_df(engine_capacity=0, price=5000000), verbose=False)
    assert pd.isna(df.loc[0, "price_per_cc"])
    assert pd.isna(df.loc[0, "mileage_density"])


def test_log_transforms_are_log1p():
    df = compute_numeric_features(make_df(mileage=25000, engine_capacity=1300), verbose=False)
    assert math.isclose(df.loc[0, "log_mileage"], np.log1p(25000), abs_tol=1e-6)
    assert math.isclose(df.loc[0, "log_engine_capacity"], np.log1p(1300), abs_tol=1e-6)


def test_log_price_not_computed_unless_requested():
    df = compute_numeric_features(make_df(), verbose=False)
    assert "log_price" not in df.columns

    df = compute_log_price(df, verbose=False)
    assert math.isclose(df.loc[0, "log_price"], np.log1p(4000000), abs_tol=1e-6)
