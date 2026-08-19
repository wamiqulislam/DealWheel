"""
tests/test_seller_keywords.py

The most important test here is test_every_flag_matches_its_own_button_text:
it's a regression guard for a real bug found during development, where
15 of the 28 seller_* keyword lists did NOT match the literal text
their own button inserts (e.g. the "Duplicate Number Plate" button
inserts "...plates available." (plural) but the suggested keyword was
"duplicate number plate" (singular), which failed to match under
whole-word matching). If this test ever fails again, a keyword list
in keyword_maps.py has regressed.
"""

import pandas as pd
import pytest

from keyword_maps import SELLER_KEYWORD_MAP
from seller_keywords import extract_seller_flags

# column -> the literal "Text it inserts" for that button, taken
# verbatim from the supplied button/keyword table.
INSERTED_TEXT = {
    "seller_genuine_condition": "Everything is in genuine condition.",
    "seller_like_new": "In showroom condition.",
    "seller_authorized_workshop": "Fully maintained through authorized dealership.",
    "seller_minor_accident": "Minor Accidental Cars.",
    "seller_service_history": "Complete service history available.",
    "seller_fresh_import": "Recently imported.",
    "seller_price_negotiable": "Price is flexible.",
    "seller_original_book": "Original book of this car is also available.",
    "seller_duplicate_book": "Original book not available.",
    "seller_original_file": "All original documents are complete.",
    "seller_duplicate_file": "File is duplicate.",
    "seller_duplicate_plate": "Duplicate number plates available.",
    "seller_non_accidental": "Never been into any accident.",
    "seller_new_tyres": "Brand new tires installed.",
    "seller_auction_sheet": "Complete auction sheet available.",
    "seller_token_paid": "All token taxes are paid to date.",
    "seller_lifetime_token": "Token tax paid for life.",
    "seller_urgent_sale": "Need to sell the car urgently.",
    "seller_driven_on_petrol": "Driven on petrol throughout.",
    "seller_factory_cng": "Company fitted CNG.",
    "seller_army_officer": "The car was in the use of an Army Officer.",
    "seller_minor_touchups": "Few paint touchups on the body.",
    "seller_engine_repaired": "Repair work was done on the engine.",
    "seller_sealed_engine": "Engine in pristine condition.",
    "seller_engine_swapped": "Engine is swapped with another engine.",
    "seller_contact_office_hours": "Call/SMS only during office hours please.",
    "seller_exchange_possible": "Exchange is possible with other car.",
    "seller_missing_file": "Missing File.",
}


def test_inserted_text_table_matches_keyword_map_keys():
    assert set(INSERTED_TEXT.keys()) == set(SELLER_KEYWORD_MAP.keys())


@pytest.mark.parametrize("column,text", list(INSERTED_TEXT.items()))
def test_every_flag_matches_its_own_button_text(column, text):
    df = pd.DataFrame({
        "description": [text],
        "seller_comments": [""],
    })
    result = extract_seller_flags(df, verbose=False)
    assert bool(result.loc[0, column]) is True, (
        f"{column}'s keyword list does not match its own button's inserted text: {text!r}"
    )


def test_flags_are_false_on_empty_text():
    df = pd.DataFrame({"description": [""], "seller_comments": [""]})
    result = extract_seller_flags(df, verbose=False)
    for column in SELLER_KEYWORD_MAP:
        assert bool(result.loc[0, column]) is False


def test_flags_are_false_on_nan_text():
    df = pd.DataFrame({"description": [None], "seller_comments": [None]})
    result = extract_seller_flags(df, verbose=False)
    for column in SELLER_KEYWORD_MAP:
        assert bool(result.loc[0, column]) is False


def test_field_boundary_does_not_bleed_across_columns():
    # "genuine" at the end of description + "condition" at the start
    # of seller_comments must NOT combine into a "genuine condition" match.
    df = pd.DataFrame({
        "description": ["This car is quite genuine"],
        "seller_comments": ["condition is fair, some wear"],
    })
    result = extract_seller_flags(df, verbose=False)
    assert bool(result.loc[0, "seller_genuine_condition"]) is False


def test_searches_both_description_and_seller_comments():
    only_description = pd.DataFrame({
        "description": ["Everything is in genuine condition."],
        "seller_comments": [""],
    })
    only_comments = pd.DataFrame({
        "description": [""],
        "seller_comments": ["Everything is in genuine condition."],
    })
    assert bool(extract_seller_flags(only_description, verbose=False).loc[0, "seller_genuine_condition"]) is True
    assert bool(extract_seller_flags(only_comments, verbose=False).loc[0, "seller_genuine_condition"]) is True
