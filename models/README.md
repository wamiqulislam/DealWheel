# PakWheels Car Price Pipeline

Turns raw scraped listings into a fully-featured table ready for
model training:

```
cars.listings  ->  cleaning  ->  feature engineering  ->  cars.processed_listings
```

This repo covers the **cleaning + feature engineering** stage end to
end. Model training, evaluation, prediction, and analysis notebooks
are scaffolded (`src/training`, `src/evaluation`, `src/prediction`,
`notebooks/`) but not yet built.

## Folder structure

```
models/
├── README.md                  <- you are here
├── requirements.txt
├── .env.example                <- copy to .env and fill in
│
├── config/
│   ├── column_manifest.py      <- single source of truth for every column name/grouping
│   └── settings.py             <- env loading + tunable assumptions
│
├── sql/                        <- reference copies of the table schemas
│   ├── 01_listings_schema.sql
│   ├── 02_processed_listings_schema.sql
│   └── 03_add_processed_listings_unique_constraint.sql   (optional, for --write-mode upsert)
│
├── src/
│   ├── preprocessing/           <- already built (null handling, color cleaning, dedupe/impossible values)
│   ├── features/                <- THIS PROJECT'S MAIN DELIVERABLE (see below)
│   ├── db/
│   │   └── database.py          <- Postgres read/write
│   ├── pipeline/
│   │   └── run_pipeline.py      <- end-to-end entry point (DB or CSV, either direction)
│   ├── training/                <- not built yet (placeholder + README)
│   ├── evaluation/               <- not built yet (placeholder + README)
│   └── prediction/               <- not built yet (placeholder + README)
│
├── data/
│   ├── raw/sample_listings.csv              <- small synthetic dataset for testing without a DB
│   ├── processed/processed_listings_sample.csv  <- that dataset's output, checked in as a reference
│   └── interim/                              <- scratch space, gitignored
│
├── notebooks/                   <- not built yet (placeholder + README)
├── saved_models/                <- not built yet (trained model artifacts go here)
├── tests/                       <- pytest suite, one file per src/features module
└── logs/
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with your Postgres credentials
```

## Running the pipeline

```bash
# Full run against Postgres (reads cars.listings, writes cars.processed_listings)
python -m src.pipeline.run_pipeline --source db --write db

# No database needed -- runs against the bundled sample CSV
python -m src.pipeline.run_pipeline \
    --source csv --input data/raw/sample_listings.csv \
    --write csv --output data/processed/processed_listings_sample.csv

# Mix and match, e.g. pull from the DB but preview to CSV first
python -m src.pipeline.run_pipeline --source db --write csv --output data/processed/preview.csv

# Quick DB smoke test on the first 500 rows
python -m src.pipeline.run_pipeline --source db --write csv --output /tmp/preview.csv --limit 500
```

Run `python -m src.pipeline.run_pipeline --help` for all flags
(`--write-mode replace|append|upsert`, `--include-log-price`, etc).

**`--write-mode replace`** (the default) truncates and rebuilds
`cars.processed_listings` from scratch every run -- always safe to
re-run, no schema changes needed. Use `--write-mode upsert` instead
only if you need incremental updates; it requires the unique
constraint in `sql/03_add_processed_listings_unique_constraint.sql`.

## Running the tests

```bash
pytest tests/
```

## What each pipeline stage does

**1. `src/preprocessing`** (pre-existing, not modified in this
round except one additive fix -- see "Notes and assumptions" below)
- `null_handler.py` -- fills electric cars' `engine_capacity` to 0,
  fills `body_type` from other listings of the same brand+model,
  fills missing `is_featured` to False, drops any row still null
  after that.
- `color_cleaner.py` -- adds a standardized `color_clean` column.
- `duplicates_impossibles.py` -- drops duplicate `listing_id`s and
  rows with impossible price/year/mileage/engine values.

**2. `src/features`** (this project's deliverable), run in this order:

| Step | Module | What it does |
|---|---|---|
| 1 | `text_cleaning.py` | Standardizes `brand`, `model`, `city`, `fuel_type`, `transmission`, `body_type`, `registered_in`, `assembly`: fixes case/whitespace, preserves known acronyms (BMW, CNG, GLi, ...), maps garbage values ("N/A", "-", "none", ...) to `"Unknown"`. |
| 2 | `seller_keywords.py` | Detects which of the 28 quick-comment buttons a seller used, by keyword-searching `description` + `seller_comments` (see `keyword_maps.py`). |
| 3 | `content_flags.py` | Broader free-text search for owner count, cosmetic condition, accident mentions, etc. (the `contains_*` columns). |
| 4 | `scores.py` | Rolls booleans up into `equipment_score`/`safety_score`/`comfort_score`/`luxury_score`/`technology_score` and `seller_confidence_score`/`seller_risk_score`/`seller_urgency_score`. |
| 5 | `numeric_features.py` | `car_age`, `mileage_per_year`, category buckets, `mileage_ratio`, log transforms, `price_per_cc`/`mileage_density`. |
| 6 | `market_features.py` | Compares each listing to others of the same brand+model+year. |
| 7 | `location_features.py` | `is_large_city`, `city_avg_price`, `city_listing_count`. |

`build_features.py` runs all seven in order (order matters -- see its
docstring) and `select_processed_columns()` picks exactly the columns
`cars.processed_listings` expects.

## Notes and assumptions (read this before trusting the numbers)

**Target leakage.** `market_avg_price`, `market_median_price`,
`market_std_price`, `market_price_difference`, `market_price_ratio`,
and `percent_below_market` are all derived from `price` (an average
over the row's own market segment, which includes the row itself).
They're computed and stored because the schema calls for them, but
`config/column_manifest.py`'s `TRAINING_FEATURES` deliberately
excludes them, and `ANALYSIS_ONLY_COLUMNS` documents why. Pull your
feature list from `TRAINING_FEATURES` when you get to `src/training`
rather than hand-listing columns, so this isn't something you have to
remember to re-exclude.

**`listing_id` gotcha.** `cars.processed_listings.listing_id` is a
foreign key to `cars.listings.id` (the internal auto-increment PK) --
**not** `cars.listings.listing_id` (the external site's ad ID). Both
columns are called "listing_id"-ish across the two tables but mean
different things. `src/db/database.py` handles this explicitly by
renaming `listings.id` to `source_pk` on read, specifically so it
never gets confused with the external ID downstream.

**Seller-keyword matching was verified against the literal
button text, not just the suggested keywords.** While building
`keyword_maps.py`, I checked every one of the 28 mapped buttons'
*actual* auto-inserted sentence against its suggested keyword, and
found 15 of them didn't actually match (e.g. the "Duplicate Number
Plate" button inserts "...plates available." (plural) but the
suggested keyword was "duplicate number plate" (singular), which
failed under whole-word matching; several buttons' suggested keyword
isn't even a substring of their own inserted text at all, e.g.
"Original Book" inserts "...also available." but the suggested
keyword is "original book available"). Every column's phrase list now
also includes the literal inserted text, and this is regression-
tested in `tests/test_seller_keywords.py` (`test_every_flag_matches_its_own_button_text`,
parametrized over all 28). The original suggested keywords are kept
too, since they still catch a seller typing the same claim in free
text without using the button.

**Several things are genuine judgment calls, not scraped facts** --
edit these if you'd draw the line differently:
- `AVERAGE_KM_PER_YEAR` (default 12,000, `config/settings.py`) --
  used for `mileage_ratio`. No authoritative source for this baked
  into the data.
- `LARGE_CITIES` (`src/features/location_maps.py`) -- which
  Pakistani cities count as "large" for `is_large_city`.
- `SAFETY_FEATURES` / `COMFORT_FEATURES` / `LUXURY_FEATURES` /
  `TECHNOLOGY_FEATURES` (`src/features/feature_groups.py`) -- the
  feature dictionary only gave examples ("ABS, airbags, TPMS,
  cameras, etc.") for these four category scores, not an exhaustive
  list, so the exact groupings are a documented judgment call. A
  feature can legitimately count toward more than one category (e.g.
  `feat_head_up_display_hud` counts as both luxury and technology) --
  it just doesn't double-count within `equipment_score`, which sums
  the raw `feat_*` flags directly.
- `SELLER_POSITIVE_FLAGS` / `SELLER_NEGATIVE_FLAGS` /
  `SELLER_URGENCY_FLAGS` (`src/features/feature_groups.py`) -- which
  `seller_*` flags feed `seller_confidence_score` /
  `seller_risk_score` / `seller_urgency_score`. Purely informational
  flags (fuel type, import status, army-officer provenance, contact
  hours) deliberately feed none of the three.
- `CONTAINS_KEYWORD_MAP` (`src/features/keyword_maps.py`) -- unlike
  the seller button table, nobody handed us a keyword list for
  `contains_first_owner` / `contains_scratch` / etc., so these are a
  reasonable starting point, not verified ground truth.

**Known limitation: no negation handling.** All keyword matching is
plain phrase search with no NLP. `"non accident"` and `"no
accidents"` both set `contains_accident = True`, even though the
second one *means* accident-free. This is an inherent limitation of
keyword search, not a bug -- flagging it so it doesn't surprise you
downstream. If it matters for a given column, cross-reference with
the more specific `seller_*` flag (e.g. `seller_non_accidental`) which
came from the actual button rather than free text.

**Defensive null handling.** `null_handler.drop_remaining_nulls()`
does a blanket `dropna()` across every column. That's correct for
columns where a NULL genuinely makes a row unusable, but a NULL raw
`color` is expected and already has its own fallback
(`color_cleaner.py` turns it into `color_clean = "Unknown"`) -- so
`src/preprocessing/clean.py`'s `clean_dataframe()` fills `title`,
`description`, `seller_comments`, `ad_url`, and `color` with `""`
*before* that dropna, so a NULL in any of them can't silently drop
the row before `color_clean`'s fallback or `src/features`'s keyword
search ever get to run. This is a defensive safety net, not a fix for
an active problem -- `description`/`seller_comments` have no NULLs in
the current dataset. Every column `null_handler.py` has dedicated
repair logic for (`engine_capacity`, `body_type`, `is_featured`) is
untouched, since that logic depends on seeing real NaNs.

**`color` vs `color_clean`.** `color_cleaner.py` adds `color_clean`
alongside the original `color` rather than overwriting it (reasonable
choice for a module that doesn't own final column selection). Since
`cars.processed_listings` only has one `color` column,
`src/pipeline/run_pipeline.py`'s `fix_color_column()` does the
rename/drop right after preprocessing runs, rather than editing
`color_cleaner.py` itself.

**`log_price` is off by default**, per the feature dictionary
("Experimental Target ... not stored unless experimenting") --
`cars.processed_listings.log_price` gets written as `NULL` unless you
pass `--include-log-price`.

**CSV testing note:** pandas' `read_csv` treats certain strings
(`"N/A"`, `"NA"`, `"null"`, `"-"`, ...) as missing values by default.
If you test with a CSV containing those literal strings in a
required column, they'll read in as real NaN and can get dropped by
`drop_remaining_nulls()` -- this doesn't happen when reading from
Postgres directly, since a real `TEXT` column containing the literal
string `"N/A"` comes back as that string, not NULL.

## Import style (why it looks the way it does)

`src/preprocessing/*.py` was supplied with plain sibling imports
(`from null_handler import clean_nulls`), and I left that untouched.
`src/features/*.py` follows the same sibling-import style for
consistency. This means both directories -- plus the project root
(for `config.*`) and `src/` itself (for `from db.database import
...`) -- need to be on `sys.path`. `src/pipeline/run_pipeline.py` and
`tests/conftest.py` both set this up explicitly in one place (see the
comment at the top of `run_pipeline.py`); everything else just uses
normal imports assuming that's already happened.
