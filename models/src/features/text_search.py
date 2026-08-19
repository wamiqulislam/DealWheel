"""
src/features/text_search.py

Small shared utilities for keyword/phrase search over free text
(description + seller_comments). Used by both seller_keywords.py and
content_flags.py so the two modules search text the exact same way.
"""

import re

import pandas as pd

# Separator inserted between concatenated text fields so a phrase
# can never accidentally match across the boundary between two
# fields (e.g. description ending in "...genuine" and seller_comments
# starting with "condition..." must NOT match "genuine condition").
FIELD_SEPARATOR = " <FIELD> "


def build_search_corpus(df, columns=("description", "seller_comments")):
    """
    Returns a lowercase Series combining the given text columns into
    one search corpus per row, safe for phrase matching.
    """
    present = [c for c in columns if c in df.columns]
    if not present:
        return pd.Series([""] * len(df), index=df.index)

    combined = df[present[0]].fillna("").astype(str)
    for col in present[1:]:
        combined = combined + FIELD_SEPARATOR + df[col].fillna("").astype(str)

    return combined.str.lower()


def _phrase_pattern(phrases):
    """Builds a single alternation regex with word boundaries around each phrase."""
    escaped = [re.escape(p.lower().strip()) for p in phrases if p.strip()]
    if not escaped:
        return None
    # Longest first so overlapping phrases don't shadow a more specific match.
    escaped.sort(key=len, reverse=True)
    return r"\b(?:" + "|".join(escaped) + r")\b"


def keyword_present(corpus, phrases):
    """
    Vectorized: True where ANY of `phrases` appears in `corpus` as a
    whole-word/whole-phrase match (case-insensitive; corpus is
    expected to already be lowercased by build_search_corpus).
    """
    pattern = _phrase_pattern(phrases)
    if pattern is None:
        return pd.Series(False, index=corpus.index)
    return corpus.str.contains(pattern, regex=True, na=False)


def apply_keyword_map(df, keyword_map, columns=("description", "seller_comments")):
    """
    Given {output_column: [phrase, phrase, ...]}, returns a DataFrame
    with one boolean column per key, True where any of its phrases
    was found in the combined search corpus for that row.
    """
    corpus = build_search_corpus(df, columns=columns)
    result = pd.DataFrame(index=df.index)
    for column_name, phrases in keyword_map.items():
        result[column_name] = keyword_present(corpus, phrases)
    return result
