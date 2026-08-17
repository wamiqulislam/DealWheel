# DealWheel Scraper (Scrapy + PostgreSQL)

Production scraper for PakWheels used-car listings. Built against the
`cars.listings` / `cars.scrape_log` schema, extended with a few new columns
and a staging table — see `migrations/0002_add_new_columns.sql`.

## Project layout

```
scrapy.cfg
requirements.txt
.env.example
migrations/
└── 0002_add_new_columns.sql   # run this once against an existing DB
dealwheel_scraper/
├── settings.py          # throttling, retries, pipelines, middlewares
├── items.py              # ListingItem field definitions
├── extractors.py         # raw HTML/JSON-LD parsing (spider-side only)
├── cleaning.py           # price/mileage/engine/text normalization
├── db_models.py          # engine, ScrapeLog ORM model, DB helpers
├── feature_columns.py    # dynamic feature_* column management
├── pipelines.py          # Validation -> Cleaning -> Postgres (upsert+log)
├── middlewares.py        # UA (one per run), proxy, random delay, block detection
└── spiders/
    ├── base_spider.py            # shared parsing, pagination, redirect detection
    ├── pakwheels_full.py         # one-pass full crawl (smaller/quicker runs)
    ├── pakwheels_discover.py     # two-phase workflow, phase 1: collect URLs
    ├── pakwheels_scrape_urls.py  # two-phase workflow, phase 2: scrape them
    └── pakwheels_incremental.py # daily incremental crawl
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in DATABASE_URL at minimum
```

Run `migrations/0002_add_new_columns.sql` against your database (adds
`registered_in`, `assembly`, `is_featured` to `cars.listings`, plus the new
`cars.discovered_urls` staging table) before using this version.

## Running it

**For the most complete initial seed (~70k+ listings)**, use the two-phase
workflow:

```bash
scrapy crawl pakwheels_discover      # phase 1: collect every listing URL (~3100 requests, fast)
scrapy crawl pakwheels_scrape_urls   # phase 2: scrape each one (slow, but immune to reordering)
```

Phase 1 only walks the search-index pages, so it finishes in a fraction of
the time a combined crawl would take. That matters because PakWheels'
listing feed reorders live as sellers renew/edit ads — the shorter phase 1
takes, the less the site can reshuffle underneath it, so the URL list it
produces is far more complete. Phase 2 never touches the search pages again,
so reordering there can't cause it to miss anything — it's just working
through a fixed list. If phase 2 gets interrupted, just re-run it; it only
re-fetches rows in `cars.discovered_urls` still marked `scraped = FALSE`.

**For smaller or quicker runs**, `pakwheels_full` still works as a single
combined pass — same underlying parsing/pipeline, just more exposed to
reordering on very long runs.

```bash
# daily, going forward
scrapy crawl pakwheels_incremental
```

To start a clean initial seed from scratch:
```sql
TRUNCATE TABLE cars.listings, cars.discovered_urls RESTART IDENTITY;
```
(`RESTART IDENTITY` resets the `id` sequence — a good practice for a clean
reseed, though it wasn't the cause of any missed listings; that was reordering
during long single-pass crawls, which the two-phase workflow addresses.)

Logs go to both the console and `logs/dealwheel_scraper.log`. Every run
writes one row to `cars.scrape_log` when it finishes (or is stopped).

## Columns added in this version

- **`registered_in`** — where the car is registered (e.g. Karachi,
  Islamabad), read from the on-page spec list. Deliberately separate from
  `city`, which is where the ad/seller currently is — registration location
  matters on its own (e.g. cars registered in humid coastal cities are
  often priced lower due to rust exposure).
- **`assembly`** — `Local` or `Imported`, as stated on the ad.
- **`is_featured`** — whether the seller paid to feature the ad (checked via
  the page's carousel/ribbon markup). `NULL` means the expected carousel
  structure wasn't found at all (distinct from a confirmed `FALSE`).

## Things worth knowing / double-checking

**Live reordering, not a code bug, was the main cause of missed listings.**
A single ~6-hour combined crawl walks through pages sorted by a still-somewhat
volatile order; sellers renewing/editing ads during that window shift
listings to different pages than where the crawl first encountered them.
Scrapy's dupefilter correctly avoids re-scraping those, but some other
listings drift out of view entirely during the run and are never landed on.
The two-phase workflow (`pakwheels_discover` + `pakwheels_scrape_urls`)
addresses this by keeping the reorder-exposed part of the crawl (walking
search pages) as short as possible, and making the slow part (detail
scraping) immune to further reordering since it works off a fixed list.

**A consistent User-Agent per run, not per request.** Rotating it on every
single request while cookies stay session-consistent (Scrapy's cookie jar
persists across a whole crawl) is an inconsistent fingerprint that some
anti-bot systems react to by quietly serving a reduced page (missing
features/seller comments) rather than an outright block. Each fresh
`scrapy crawl` picks a new random UA, but uses it consistently for that
entire run.

**Pagination redirect detection.** If a search-page request lands on a
different `page=N` than requested (PakWheels redirecting once you're deep
enough into `?page=N` pagination), the spider now detects this explicitly,
logs why, and stops paginating cleanly instead of silently looping into
already-visited pages.

**`ROBOTSTXT_OBEY` is `False`** — check `https://www.pakwheels.com/robots.txt`
yourself if you want Scrapy to respect it instead.

**Feature columns** are added on the fly, one `BOOLEAN` column per feature
seen (`feat_air_conditioning`, `feat_abs`, ...) — fine as long as PakWheels'
feature vocabulary stays a small, consistent set of checkboxes. If your
database has any of these left over as `smallint` from an earlier version,
run `migrations/0003_fix_feature_column_types.sql` (no-op if they're already
boolean).
feature vocabulary stays a small, consistent set of checkboxes.

**Three-layer field extraction** (JSON-LD → on-page spec list → meta
description sentence → title-based brand/model/year guess) — see the
docstring at the top of `extractors.py` for exactly which layer supplies
which fields, and the known limitation with genuine two-word brands (e.g.
"Land Rover") in the title-based guess.
