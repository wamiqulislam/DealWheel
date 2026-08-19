"""
src/features/keyword_maps.py

Reference data used by seller_keywords.py and content_flags.py.

SELLER_KEYWORD_MAP
-------------------
PakWheels' "add a comment" UI has a fixed set of quick-select buttons.
Clicking one inserts a fixed sentence into seller_comments (e.g.
clicking "Bumper-to-Bumper Original" inserts "Everything is in
genuine condition."). This dict maps each resulting
cars.processed_listings.seller_* column to the list of keyword
phrases (from the supplied button/keyword table) that should be
searched for in description + seller_comments to detect that a
seller selected that option -- searching on the keywords rather than
only the exact inserted sentence also catches sellers who typed the
same claim in free text instead of using the button.

Only 28 of the 29 buttons map onto a processed_listings column:
"Alloy Rims" is deliberately excluded here because it duplicates
information already captured by the scraped feat_alloy_wheels flag,
and there is no seller_alloy_rims column in the schema.

CONTAINS_KEYWORD_MAP
---------------------
Keyword phrases for the broader, free-text contains_* columns. These
are NOT tied to a specific quick-comment button -- they're plain
keyword/phrase searches over description + seller_comments for
concepts the feature dictionary calls out (owner count, cosmetic
condition, accident history, seal/token mentions, usage type). Unlike
the seller_* flags, this list was not handed to us directly, so it's
a reasonable, editable starting point -- tune it if you find false
positives/negatives once you inspect real listings.

All phrases are plain lowercase substrings/words. They are matched
with regex word boundaries in keyword_search.py so "own" doesn't
match inside "owner", etc. -- multi-word phrases just need to appear
in order.
"""

# column_name -> list of keyword phrases (lowercase)
#
# For every column, this list includes:
#   (a) the suggested keyword(s) from the supplied button table, and
#   (b) the literal "Text it inserts" sentence for that button
#       (verbatim, trailing period dropped)
#
# (b) matters more than it looks: 15 of the 28 buttons' own inserted
# sentences do NOT contain their own "suggested keyword" as a
# contiguous phrase (e.g. button #9 inserts "Original book of this
# car is also available." but its suggested keyword is "original
# book available" -- not a substring of that sentence; button #4
# inserts "Minor Accidental Cars." but its keyword is "minor
# accident", which fails word-boundary matching against
# "Accidental"). Relying on the suggested keyword alone would silently
# miss the exact case these flags exist to catch: a seller who
# actually clicked the button. Every phrase list below was verified
# programmatically to match its own button's inserted text.
SELLER_KEYWORD_MAP = {
    "seller_genuine_condition": [
        "genuine condition", "bumper to bumper",
    ],
    "seller_like_new": [
        "showroom condition", "like new",
    ],
    "seller_authorized_workshop": [
        "authorized workshop", "authorized dealership",
    ],
    "seller_minor_accident": [
        "minor accident", "minor accidental",
    ],
    "seller_service_history": [
        "service history",
    ],
    "seller_fresh_import": [
        "fresh import", "recently imported",
    ],
    "seller_price_negotiable": [
        "price negotiable", "price flexible", "price is flexible",
    ],
    "seller_original_book": [
        "original book available", "book of this car is also available",
    ],
    "seller_duplicate_book": [
        "duplicate book", "original book not available",
    ],
    "seller_original_file": [
        "original file", "complete file", "original documents are complete",
    ],
    "seller_duplicate_file": [
        "duplicate file", "file is duplicate",
    ],
    "seller_duplicate_plate": [
        "duplicate number plate", "duplicate number plates",
    ],
    "seller_non_accidental": [
        "non accident", "accident free", "never been into any accident",
    ],
    "seller_new_tyres": [
        "new tires", "new tyres",
    ],
    "seller_auction_sheet": [
        "auction sheet",
    ],
    "seller_token_paid": [
        "token tax paid", "up to date", "token taxes are paid to date",
    ],
    "seller_lifetime_token": [
        "lifetime token", "token tax paid for life",
    ],
    "seller_urgent_sale": [
        "urgent sale", "urgently",
    ],
    "seller_driven_on_petrol": [
        "driven on petrol",
    ],
    "seller_factory_cng": [
        "factory fitted cng", "company fitted cng",
    ],
    "seller_army_officer": [
        "army officer",
    ],
    "seller_minor_touchups": [
        "touch up", "paint touch", "touchups on the body",
    ],
    "seller_engine_repaired": [
        "engine repair", "repair work was done on the engine",
    ],
    "seller_sealed_engine": [
        "pristine engine", "sealed engine", "engine in pristine condition",
    ],
    "seller_engine_swapped": [
        "engine swapped", "engine is swapped with another engine",
    ],
    "seller_contact_office_hours": [
        "office hours",
    ],
    "seller_exchange_possible": [
        "exchange possible", "exchange is possible with other car",
    ],
    "seller_missing_file": [
        "missing file",
    ],
}

CONTAINS_KEYWORD_MAP = {
    "contains_first_owner": ["first owner", "1st owner"],
    "contains_second_owner": ["second owner", "2nd owner"],
    "contains_single_owner": ["single owner", "single hand", "one hand owner"],
    "contains_scratch": ["scratch", "scratches", "scratched"],
    "contains_paint": ["paint", "painted", "repainted", "repaint", "paintwork"],
    "contains_touchup": ["touch up", "touchup", "touch-up", "touchups", "touch ups"],
    "contains_accident": ["accident", "accidental", "accidents"],
    "contains_seal": ["seal open", "seal broken", "chassis seal", "sealed", "seal intact"],
    "contains_token": ["token", "tokens"],
    "contains_family_use": ["family used", "family use", "family car", "used by family"],
    "contains_home_used": ["home used", "home use", "personal use", "personal car"],
}
