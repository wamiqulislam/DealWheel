import pandas as pd

from content_flags import extract_contains_flags


def make_df(description="", seller_comments=""):
    return pd.DataFrame({"description": [description], "seller_comments": [seller_comments]})


def test_owner_flags():
    df = extract_contains_flags(make_df(description="first owner car"), verbose=False)
    assert bool(df.loc[0, "contains_first_owner"]) is True
    assert bool(df.loc[0, "contains_second_owner"]) is False

    df = extract_contains_flags(make_df(description="this is a 2nd owner vehicle"), verbose=False)
    assert bool(df.loc[0, "contains_second_owner"]) is True


def test_scratch_paint_touchup():
    df = extract_contains_flags(
        make_df(description="minor scratches and a small paint touchup on the bumper"), verbose=False
    )
    assert bool(df.loc[0, "contains_scratch"]) is True
    assert bool(df.loc[0, "contains_paint"]) is True
    assert bool(df.loc[0, "contains_touchup"]) is True


def test_accident_word_forms():
    df = extract_contains_flags(make_df(description="no major accidents reported"), verbose=False)
    assert bool(df.loc[0, "contains_accident"]) is True

    df = extract_contains_flags(make_df(description="minor accidental damage"), verbose=False)
    assert bool(df.loc[0, "contains_accident"]) is True


def test_no_false_positive_on_unrelated_text():
    df = extract_contains_flags(make_df(description="reliable family sedan, well maintained"), verbose=False)
    # "family" alone (without "used"/"use"/"car") should not trigger contains_family_use
    assert bool(df.loc[0, "contains_family_use"]) is False


def test_family_and_home_use():
    df = extract_contains_flags(make_df(description="family used, home use only"), verbose=False)
    assert bool(df.loc[0, "contains_family_use"]) is True
    assert bool(df.loc[0, "contains_home_used"]) is True
