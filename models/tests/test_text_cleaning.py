import pandas as pd

from text_cleaning import standardize_text_value, clean_text_columns


def test_case_and_whitespace():
    assert standardize_text_value("  toyota  ") == "Toyota"
    assert standardize_text_value("TOYOTA") == "Toyota"
    assert standardize_text_value("Corolla   GLi") == "Corolla GLi"


def test_acronyms_preserved():
    assert standardize_text_value("bmw") == "BMW"
    assert standardize_text_value("cng") == "CNG"
    assert standardize_text_value("mercedes-benz") == "Mercedes-Benz"


def test_garbage_values_become_unknown():
    for value in ["", "N/A", "none", "null", "-", "unknown", None]:
        assert standardize_text_value(value) == "Unknown"


def test_nan_becomes_unknown():
    assert standardize_text_value(float("nan")) == "Unknown"


def test_clean_text_columns_only_touches_listed_columns():
    df = pd.DataFrame({
        "brand": ["toyota"],
        "description": ["should NOT be touched: toyota"],
    })
    cleaned = clean_text_columns(df, columns=["brand"], verbose=False)
    assert cleaned.loc[0, "brand"] == "Toyota"
    assert cleaned.loc[0, "description"] == "should NOT be touched: toyota"


def test_clean_text_columns_skips_missing_columns():
    df = pd.DataFrame({"brand": ["toyota"]})
    # should not raise even though "city" isn't in df
    cleaned = clean_text_columns(df, columns=["brand", "city"], verbose=False)
    assert cleaned.loc[0, "brand"] == "Toyota"
