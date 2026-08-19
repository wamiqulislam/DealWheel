"""
src/features/content_flags.py

Broader free-text signal extraction (owner count, cosmetic condition,
accident mentions, seal/token mentions, usage type), independent of
the fixed quick-comment buttons handled in seller_keywords.py. See
keyword_maps.CONTAINS_KEYWORD_MAP for the phrase lists.

Produces one boolean column per entry in config.column_manifest.CONTAINS_COLUMNS.
"""

from config.column_manifest import CONTAINS_COLUMNS
from keyword_maps import CONTAINS_KEYWORD_MAP
from text_search import apply_keyword_map


def extract_contains_flags(df, verbose=True):
    """Returns a copy of df with all contains_* flag columns added."""
    df = df.copy()
    flags = apply_keyword_map(df, CONTAINS_KEYWORD_MAP)

    for column in flags.columns:
        df[column] = flags[column]

    if verbose:
        hits = {c: int(df[c].sum()) for c in CONTAINS_COLUMNS if c in df.columns}
        top = sorted(hits.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print(f"[content_flags] {len(CONTAINS_COLUMNS)} flags extracted. Top hits: {top}")

    return df
