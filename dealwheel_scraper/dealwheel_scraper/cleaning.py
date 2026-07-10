"""
Normalization helpers used by CleaningPipeline and FeatureColumnManager.

These are pure functions (no I/O) so they're trivial to unit test on their own,
e.g.:

    >>> clean_price("PKR 42.7 lacs")
    4270000
    >>> clean_number("80,000 km")
    80000
"""
from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_NUMERIC_RE = re.compile(r"[\d,]+(?:\.\d+)?")
_YEAR_RE = re.compile(r"(19|20)\d{2}")
_LAC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lacs?|lakhs?)\b", re.IGNORECASE)
_CRORE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", re.IGNORECASE)


def clean_text(value) -> str | None:
    """Strips whitespace/unicode noise. Returns None for empty/missing values
    so they map cleanly onto SQL NULL instead of empty strings."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = _WHITESPACE_RE.sub(" ", value).strip()
    return value or None


def clean_year(value) -> int | None:
    """'2017', '2017-01-01', 'Model 2017' -> 2017"""
    if value is None:
        return None
    match = _YEAR_RE.search(str(value))
    return int(match.group(0)) if match else None


def clean_number(value) -> int | None:
    """'80,000 km' -> 80000, '1800 cc' -> 1800, 4270000 -> 4270000"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = _NUMERIC_RE.search(str(value))
    if not match:
        return None
    try:
        return int(float(match.group(0).replace(",", "")))
    except ValueError:
        return None


def clean_price(value) -> int | None:
    """
    Normalizes PakWheels-style price strings/numbers to a plain PKR integer.
      "PKR 4,350,000"  -> 4350000
      "PKR 42.7 lacs"  -> 4270000
      "1.2 crore"      -> 12000000
      4270000          -> 4270000   (already-numeric JSON-LD price)
      "Call for price" -> None
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip()
    if not text:
        return None

    crore_match = _CRORE_RE.search(text)
    if crore_match:
        return int(float(crore_match.group(1)) * 10_000_000)

    lac_match = _LAC_RE.search(text)
    if lac_match:
        return int(float(lac_match.group(1)) * 100_000)

    return clean_number(text)


def slugify_feature(name: str, prefix: str = "feat_", max_length: int = 63) -> str:
    """'Air Conditioning' -> 'feat_air_conditioning' (safe Postgres identifier)."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"{prefix}{slug}"[:max_length]
