# DealWheel Scraper (Scrapy + PostgreSQL)

Production scraper for PakWheels used-car listings: a one-time full crawl to
seed the database, plus a daily incremental crawl that only pulls in what's
new. Built against the `cars.listings` / `cars.scrape_log` schema you already
have in Postgres.

## Project layout

```
scrapy.cfg
requirements.txt
.env.example
dealwheel_scraper/
├── settings.py          # throttling, retries, pipelines, middlewares
├── items.py              # ListingItem field definitions
├── extractors.py         # raw HTML/JSON-LD parsing (spider-side only)
├── cleaning.py           # price/mileage/engine/text normalization
├── db_models.py          # engine, ScrapeLog ORM model, DB helpers
├── feature_columns.py    # dynamic feature_* column management
├── pipelines.py          # Validation -> Cleaning -> Postgres (upsert+log)
├── middlewares.py        # UA rotation, proxy, random delay, block detection
└── spiders/
    ├── base_spider.py           # shared listing-page parsing
    ├── pakwheels_full.py        # one-time full crawl
    └── pakwheels_incremental.py # daily incremental crawl
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then fill in DATABASE_URL at minimum
```

Your Postgres schema/tables (the `cars.listings` / `cars.scrape_log` DDL you
already wrote) need to exist before you run either spider — this project
doesn't create them.

## Running it

```bash
# once, to seed the database (~70k listings — expect this to take a long time
# given the intentional rate limiting)
scrapy crawl pakwheels_full

# daily, going forward
scrapy crawl pakwheels_incremental
```

Logs go to both the console and `logs/dealwheel_scraper.log` (configurable
via `LOG_FILE`/`LOG_LEVEL` in `.env`). Every run — full or incremental — also
writes one row to `cars.scrape_log` when it finishes (or is stopped), with
counts and duration.

Scheduling this with cron/GitHub Actions is intentionally left for later,
per your notes — both spiders are plain `scrapy crawl` commands, so wiring
that up later is just a scheduler entry, no code changes needed.

## Things worth knowing / double-checking

**`ROBOTSTXT_OBEY` is `False`.** I wasn't able to fetch pakwheels.com's
current robots.txt from here to check what it allows. Your old
requests+BeautifulSoup scraper didn't check it either. Take a look at
`https://www.pakwheels.com/robots.txt` yourself and flip the setting in
`settings.py` if you'd rather Scrapy respect it — also worth a quick look at
their Terms of Service if you haven't already, independent of robots.txt.

**The "sort by newest" assumption doesn't hold, so the incremental spider
works differently than the spec sketch.** I checked the live search page —
PakWheels' sort dropdown only offers *Updated Date* (`bumped_at-desc/asc`),
price, model year, and mileage. There's no "date posted"/listing-ID sort.
`bumped_at` reflects the last time a listing was renewed/bumped, not when it
was created, so a recently-renewed old listing can appear ahead of a
brand-new one — "stop at the first listing_id you've already seen" isn't
reliable here, because IDs aren't in strict order in this feed.

Instead, `PostgresPipeline` tracks how many **consecutive** listings in a row
it just upserted as "already existed," and closes the spider once that streak
hits `duplicate_stop_threshold` (50, i.e. roughly two pages of nothing new) —
set on `PakwheelsIncrementalSpider` only, so the full crawl never stops early.
There's also a hard `MAX_PAGES` cap as a backstop. Tune both in
`spiders/pakwheels_incremental.py` once you've watched a few real runs and
have a feel for how "bumpy" the feed actually is.

**Feature columns are added per the spec (one `SMALLINT` column per feature,
default 0), not a JSONB catch-all.** This is fine as long as PakWheels'
feature vocabulary stays a small, consistent set of checkboxes (Air
Conditioning, ABS, Power Steering, etc.) — if you ever see it fragment into
many near-duplicate names, an `extra_specs JSONB` column would scale better
than one column per variant. Easy to add later if needed.

**The on-page spec list (`#scroll_car_detail`) is only used as a fallback**
to fill in anything JSON-LD is missing for your existing fixed columns
(mileage, transmission, color, etc.) — it is *not* turned into extra DB
columns. Only the separate feature checklist (`.car-feature-list`) drives
`feature_*` columns, per your spec.

**Concurrency/delay defaults**: `CONCURRENT_REQUESTS=16`, random delay
1.8–3.7s per request, AutoThrottle on top as a second layer that backs off
further if PakWheels starts responding slowly. All tunable via `.env` without
touching code.

## What I verified live vs. what's carried over from your old code

Verified against the current site: the `a.car-name` link selector on search
result pages, the `?sortby=` values, and that `/used-cars/search/-/` is the
right listing index with `page` as the pagination parameter.

Carried over from your existing (working) BeautifulSoup scraper without
independent re-verification here: the JSON-LD field names
(`brand`/`model`/`modelDate`/`mileageFromOdometer`/`vehicleEngine.engineDisplacement`/etc.),
the `#scroll_car_detail` spec-list structure, and the `.car-feature-list` /
`#scroll_seller_comments` selectors. Worth running `pakwheels_full` against a
small page-limit first (e.g. temporarily cap pages in the spider) to confirm
a handful of rows land in Postgres looking right before letting it run
unattended against all ~70k listings.
