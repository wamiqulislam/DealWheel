"""
color_cleaner.py

Standardizes the raw `color` column into a clean `color_clean` column
(White, Black, Silver, Grey, Blue, Red, Green, Brown, Beige, Gold,
Yellow, Orange, Purple, Pink, Bronze, Multi, or Unknown).

Pipeline for a single value (standardize_color):
    1. normalize            - lowercase, strip punctuation/whitespace
    2. fix spelling          - correct common misspellings
    3. garbage check         - "n/a", "none", "unknown" etc. -> Unknown
    4. multi-color check     - two-tone / multiple colors -> Multi
    5. Urdu color words      -> canonical color
    6. direct color word     - canonical word present in value -> that color
    7. special color name    - e.g. "olive" -> Green
    8. fallback              -> Unknown

Only ever reads the `color` column - never title, description, model, etc.
"""

import re
import unicodedata

import pandas as pd

from color_maps import CANONICAL_COLORS, SPECIAL_COLORS, URDU_COLORS, SPELLING_FIXES

GARBAGE_VALUES = {
    "none", "null", "nan", "blank", "unknown", "unlisted", "unlist",
    "not sure", "other", "any color", "any colour", "none listed",
    "not available", "n a", "na",
}

MULTICOLOR_PATTERNS = [
    r"\btwo tone\b", r"\b2 tone\b", r"\bdual tone\b", r"\bmulti\b",
    r"\bmulticolor\b", r"\bmulti colour\b", r"\bmulti color\b",
    r"\bmultiple colours?\b", r"\bmultiple colors?\b", r"\bdubbel shade\b",
]

DIRECT_COLOR_PATTERNS = [
    ("White", "white"), ("Black", "black"), ("Silver", "silver"),
    ("Grey", "grey"), ("Grey", "gray"), ("Blue", "blue"), ("Red", "red"),
    ("Green", "green"), ("Brown", "brown"), ("Beige", "beige"),
    ("Gold", "gold"), ("Yellow", "yellow"), ("Orange", "orange"),
    ("Purple", "purple"), ("Pink", "pink"), ("Bronze", "bronze"),
]


def normalize_color_value(raw_color):
    """Lowercase + strip punctuation/whitespace. Keeps English & Urdu chars."""
    if pd.isna(raw_color):
        return ""

    color = str(raw_color).strip()
    if not color:
        return ""

    color = unicodedata.normalize("NFKC", color).lower()
    color = re.sub(r"[^\w\s&+/-]", " ", color, flags=re.UNICODE)
    color = color.replace("-", " ").replace("/", " ")
    color = re.sub(r"\s+", " ", color).strip()
    return color


def fix_color_spelling(color):
    for wrong, correct in sorted(SPELLING_FIXES.items(), key=lambda x: len(x[0]), reverse=True):
        color = re.sub(rf"\b{re.escape(wrong)}\b", correct, color)
    return color


def detect_urdu_color(color):
    for word, canonical in sorted(URDU_COLORS.items(), key=lambda x: len(x[0]), reverse=True):
        if word in color:
            return canonical
    return None


def is_multicolor_value(color):
    for pattern in MULTICOLOR_PATTERNS:
        if re.search(pattern, color):
            return True

    if re.search(r"\s&\s", color):
        return True

    detected = {c for c in CANONICAL_COLORS if re.search(rf"\b{re.escape(c)}\b", color)}
    if len(detected) >= 2:
        return True

    if re.search(r"\band\b|\bwith\b", color) and len(detected) >= 1:
        return True

    return False


def detect_direct_color(color):
    """Substring match, e.g. 'metallicblue' -> 'blue' -> Blue."""
    for canonical, word in DIRECT_COLOR_PATTERNS:
        if word in color:
            return canonical
    return None


def detect_special_color(color):
    """Used only when the canonical color word itself wasn't found."""
    for name, canonical in sorted(SPECIAL_COLORS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", color):
            return canonical
    return None


def standardize_color(raw_color):
    color = normalize_color_value(raw_color)
    if not color:
        return "Unknown"

    color = fix_color_spelling(color)

    if color in GARBAGE_VALUES:
        return "Unknown"

    # Pure numbers / punctuation with no letters at all.
    if not re.search(r"[a-zA-Z\u0600-\u06FF]", color):
        return "Unknown"

    if is_multicolor_value(color):
        return "Multi"

    urdu_color = detect_urdu_color(color)
    if urdu_color:
        return urdu_color

    direct_color = detect_direct_color(color)
    if direct_color:
        return direct_color

    special_color = detect_special_color(color)
    if special_color:
        return special_color

    return "Unknown"


def clean_color_column(df, column="color", verbose=True):
    """
    Adds a `color_clean` column derived from `column`.
    Prints a short summary: how many values changed vs stayed the same,
    and how many ended up Unknown.
    """
    if column not in df.columns:
        raise ValueError(f"Color column '{column}' does not exist.")

    df = df.copy()
    df["color_clean"] = df[column].apply(standardize_color)

    original = df[column].fillna("").astype(str).str.strip().str.lower()
    cleaned = df["color_clean"].fillna("Unknown").astype(str).str.lower()
    changed_count = int((original != cleaned).sum())
    unknown_count = int((df["color_clean"] == "Unknown").sum())

    if verbose:
        print(f"[color] {changed_count:,}/{len(df):,} values standardized, {unknown_count:,} left as 'Unknown'")

    return df
