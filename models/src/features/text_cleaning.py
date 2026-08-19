"""
src/features/text_cleaning.py

Light standardization for the text/categorical columns that will
become model categories: brand, model, city, fuel_type, transmission,
body_type, registered_in, assembly.

This runs AFTER src/preprocessing (null handling, color cleaning,
duplicate/impossible-value removal) -- by this point the data is
already fairly clean. This module is a safety net, not a rewrite:
    1. Fix unicode, strip stray whitespace, collapse internal
       double-spaces.
    2. Normalize casing to Title Case (e.g. "toyota" / "TOYOTA" /
       " Toyota " -> "Toyota") so the same real-world category isn't
       split into several string variants.
    3. Preserve known acronyms (BMW, CNG, LPG, ...) that Title Case
       would otherwise mangle (Title Case turns "BMW" into "Bmw").
    4. Map obvious garbage values ("N/A", "-", "none", "null", "") to
       "Unknown" -- consistent with how color_cleaner.py already
       handles unusable color values. "Unknown" is used instead of a
       real NaN because null_handler.drop_remaining_nulls() already
       ran earlier in the pipeline; reintroducing NaNs here would
       silently drop otherwise-good rows if this module's output is
       ever run back through that step, and would need to be
       null-handled again before writing to a NOT-NULL-ish column.

Only touches the columns listed in TEXT_COLUMNS -- never description
or seller_comments (those are read, not rewritten, by the keyword
search modules) and never color (already standardized into
color_clean by color_cleaner.py).
"""

import re
import unicodedata

import pandas as pd

TEXT_COLUMNS = [
    "brand",
    "model",
    "city",
    "fuel_type",
    "transmission",
    "body_type",
    "registered_in",
    "assembly",
]

GARBAGE_VALUES = {
    "", "n/a", "na", "n a", "none", "null", "nan", "unknown",
    "not available", "not applicable", "-", "--", "?", "unspecified",
}

# Tokens Title Case would otherwise mangle (Title Case -> "Bmw", "Cng").
# Keys are lowercase; values are the correct display form.
KNOWN_ACRONYMS = {
    "bmw": "BMW",
    "mg": "MG",
    "kia": "KIA",
    "jac": "JAC",
    "faw": "FAW",
    "dfsk": "DFSK",
    "baic": "BAIC",
    "suv": "SUV",
    "cng": "CNG",
    "lpg": "LPG",
    "hev": "HEV",
    "phev": "PHEV",
    "bev": "BEV",
    "ev": "EV",
    "awd": "AWD",
    "fwd": "FWD",
    "rwd": "RWD",
    "4wd": "4WD",
    # Common trim/spec codes that show up inside `model` on the
    # Pakistani market (e.g. "Corolla GLi") -- Title Case would
    # otherwise turn these into "Gli", "Xli", etc.
    "gli": "GLi",
    "xli": "XLi",
    "vvti": "VVTi",
    "vxr": "VXR",
    "glx": "GLX",
    "cvt": "CVT",
}


def _normalize_whitespace(value):
    value = unicodedata.normalize("NFKC", value)
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _capitalize_token(token):
    """Capitalizes a single token, and each side of an internal hyphen
    (e.g. "benz" -> "Benz", "mercedes-benz" -> "Mercedes-Benz")."""
    if not token:
        return token
    parts = token.split("-")
    return "-".join(p[:1].upper() + p[1:].lower() if p else p for p in parts)


def _apply_title_case_preserving_acronyms(value):
    if not value:
        return value
    words = value.split(" ")
    fixed_words = []
    for word in words:
        # Strip trailing/leading punctuation (e.g. "cng," -> "cng") only
        # for the acronym lookup, then reattach it, so "CNG," still works.
        core = re.sub(r"[^\w-]", "", word.lower())
        if core in KNOWN_ACRONYMS:
            fixed_words.append(word.lower().replace(core, KNOWN_ACRONYMS[core]))
        else:
            fixed_words.append(_capitalize_token(word))
    return " ".join(fixed_words)


def standardize_text_value(raw_value):
    """Cleans a single text/categorical value. Public so it's easy to unit test."""
    if pd.isna(raw_value):
        return "Unknown"

    value = str(raw_value)
    value = _normalize_whitespace(value)

    if not value or value.lower() in GARBAGE_VALUES:
        return "Unknown"

    value = _apply_title_case_preserving_acronyms(value)
    return value


def clean_text_columns(df, columns=None, verbose=True):
    """
    Returns a copy of df with each column in `columns` standardized
    via standardize_text_value. Defaults to TEXT_COLUMNS. Columns not
    present in df are silently skipped (keeps this safe to call on
    partial/test frames).
    """
    df = df.copy()
    columns = columns if columns is not None else TEXT_COLUMNS

    for column in columns:
        if column not in df.columns:
            continue

        original = df[column].fillna("").astype(str).str.strip()
        df[column] = df[column].apply(standardize_text_value)

        if verbose:
            changed = int((original != df[column]).sum())
            unknown = int((df[column] == "Unknown").sum())
            print(f"[text] {column}: {changed:,}/{len(df):,} values standardized, {unknown:,} set to 'Unknown'")

    return df
