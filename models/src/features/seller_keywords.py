"""
src/features/seller_keywords.py

Detects which of PakWheels' quick-comment buttons a seller used, by
keyword-searching description + seller_comments (see keyword_maps.py
for the button -> keyword mapping and the reasoning behind it).

Produces one boolean column per entry in config.column_manifest.SELLER_FLAG_COLUMNS.
"""

from config.column_manifest import SELLER_FLAG_COLUMNS
from keyword_maps import SELLER_KEYWORD_MAP
from text_search import apply_keyword_map


def extract_seller_flags(df, verbose=True):
    """Returns a copy of df with all seller_* flag columns added."""
    df = df.copy()
    flags = apply_keyword_map(df, SELLER_KEYWORD_MAP)

    for column in flags.columns:
        df[column] = flags[column]

    if verbose:
        hits = {c: int(df[c].sum()) for c in SELLER_FLAG_COLUMNS if c in df.columns}
        top = sorted(hits.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print(f"[seller_keywords] {len(SELLER_FLAG_COLUMNS)} flags extracted. Top hits: {top}")

    return df
