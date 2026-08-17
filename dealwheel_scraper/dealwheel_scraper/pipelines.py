"""
Pipeline chain (see settings.ITEM_PIPELINES for order):
    ValidationPipeline -> CleaningPipeline -> PostgresPipeline

Spiders only extract raw data (see extractors.py); all validation, cleaning,
duplicate handling and persistence happens here.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from itemadapter import ItemAdapter
from scrapy.exceptions import CloseSpider, DropItem
from sqlalchemy import text
from twisted.internet.threads import deferToThread

from . import cleaning
from .db_models import get_engine, insert_scrape_log
from .feature_columns import FeatureColumnManager

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Drops items missing the fields we need to identify/store them at all.
    Everything else is allowed through — PakWheels ads legitimately vary in
    how much detail sellers fill in."""

    REQUIRED_FIELDS = ("listing_id", "ad_url")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field in self.REQUIRED_FIELDS:
            if not adapter.get(field):
                raise DropItem(f"Missing required field '{field}' for {adapter.get('ad_url', 'unknown URL')}")
        return item


class CleaningPipeline:
    """Normalizes raw scraped strings into clean, typed values."""

    TEXT_FIELDS = (
        "title", "city", "brand", "model", "color", "body_type",
        "fuel_type", "transmission", "description", "seller_comments",
        "registered_in", "assembly",
    )

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        for field in self.TEXT_FIELDS:
            adapter[field] = cleaning.clean_text(adapter.get(field))

        adapter["year"] = cleaning.clean_year(adapter.get("year_raw"))
        adapter["mileage"] = cleaning.clean_number(adapter.get("mileage_raw"))
        adapter["engine_capacity"] = cleaning.clean_number(adapter.get("engine_capacity_raw"))
        adapter["price"] = cleaning.clean_price(adapter.get("price_raw"))

        raw_features = adapter.get("features") or []
        cleaned_features = [cleaning.clean_text(f) for f in raw_features]
        adapter["features"] = [f for f in cleaned_features if f]

        return item


class PostgresPipeline:
    """
    Duplicate detection + persistence in a single atomic
    INSERT ... ON CONFLICT (listing_id) DO UPDATE. Combining "check" and
    "insert" into one statement avoids a check-then-act race condition while
    still fulfilling "skip if it exists, insert if it doesn't" — an existing
    row gets its mutable fields (price, mileage, description, ...) refreshed
    and scrape_date bumped, rather than being skipped outright, which is what
    lets updated_ads in scrape_log mean something.

    Feature columns are added on the fly via FeatureColumnManager. For an
    INSERT, any feature_* column not mentioned keeps its table DEFAULT of
    FALSE; for an UPDATE we explicitly set every known feature_* column to
    TRUE/FALSE so a feature that disappeared from a re-scraped ad doesn't
    linger as stale TRUE.

    Also best-effort marks the corresponding row in cars.discovered_urls as
    scraped, if one exists — used by the two-phase full-crawl workflow
    (pakwheels_discover + pakwheels_scrape_urls) to track progress and allow
    resuming an interrupted run. This is a no-op (not an error) for listings
    scraped via pakwheels_full or pakwheels_incremental, which don't use that
    staging table.
    """

    FIXED_COLUMNS = (
        "listing_id", "title", "brand", "model", "year", "city", "mileage",
        "fuel_type", "transmission", "engine_capacity", "color", "body_type",
        "price", "ad_url", "description", "seller_comments",
        "registered_in", "assembly", "is_featured",
    )

    def __init__(self):
        self.engine = None
        self.feature_manager = None
        self.stats = {"scraped": 0, "new": 0, "updated": 0, "errors": 0}
        self.consecutive_existing = 0
        self.start_time = None
        self.stop_reason = "completed"

    def open_spider(self, spider):
        self.engine = get_engine()
        self.feature_manager = FeatureColumnManager(self.engine)
        self.start_time = datetime.now(timezone.utc)
        spider.logger.info("PostgresPipeline ready (%d known feature columns).",
                            len(self.feature_manager.known_feature_columns))

    def close_spider(self, spider):
        end_time = datetime.now(timezone.utc)
        duration = int((end_time - self.start_time).total_seconds())
        notes = (f"spider={spider.name}; stop_reason={self.stop_reason}; "
                 f"errors={self.stats['errors']}")
        try:
            insert_scrape_log(
                self.engine,
                scrape_start=self.start_time,
                scrape_end=end_time,
                ads_scraped=self.stats["scraped"],
                new_ads=self.stats["new"],
                updated_ads=self.stats["updated"],
                duration_seconds=duration,
                notes=notes,
            )
        except Exception:
            spider.logger.exception("Failed to write scrape_log entry.")

        spider.logger.info(
            "Crawl finished: scraped=%d new=%d updated=%d errors=%d duration=%ds",
            self.stats["scraped"], self.stats["new"], self.stats["updated"],
            self.stats["errors"], duration,
        )
        if self.engine:
            self.engine.dispose()

    def process_item(self, item, spider):
        return deferToThread(self._process_item_sync, item, spider)

    def _process_item_sync(self, item, spider):
        adapter = ItemAdapter(item)
        fixed_values = {col: adapter.get(col) for col in self.FIXED_COLUMNS}

        present_slugs = self.feature_manager.ensure_columns(adapter.get("features") or [])
        all_known = self.feature_manager.known_feature_columns
        # Sent as Python bool (True/False), not int 0/1 — cars.listings'
        # feat_* columns are BOOLEAN, and Postgres won't implicitly cast an
        # integer to boolean in a parameterized INSERT/UPDATE.
        feature_values = {slug: (slug in present_slugs) for slug in all_known}

        try:
            inserted = self._upsert(fixed_values, feature_values)
            self.stats["scraped"] += 1
            if inserted:
                self.stats["new"] += 1
                self.consecutive_existing = 0
            else:
                self.stats["updated"] += 1
                self.consecutive_existing += 1
        except Exception:
            self.stats["errors"] += 1
            spider.logger.exception("DB error storing listing_id=%s", fixed_values.get("listing_id"))
            raise DropItem("Database error storing item")

        # Only the incremental spider sets this attribute (see
        # spiders/pakwheels_incremental.py) — the full crawl should never stop
        # early just because it re-encounters something already in the DB.
        threshold = getattr(spider, "duplicate_stop_threshold", None)
        if threshold and self.consecutive_existing >= threshold:
            self.stop_reason = f"caught_up ({self.consecutive_existing} consecutive existing listings)"
            spider.logger.info(
                "%d consecutive already-known listings — stopping incremental crawl.",
                self.consecutive_existing,
            )
            raise CloseSpider(self.stop_reason)

        return item

    def _upsert(self, fixed_values: dict, feature_values: dict) -> bool:
        """Returns True if this was a fresh insert, False if it updated an existing row."""
        columns = list(fixed_values.keys()) + list(feature_values.keys())
        values = {**fixed_values, **feature_values}

        col_sql = ", ".join(f'"{c}"' for c in columns)
        val_sql = ", ".join(f":{c}" for c in columns)
        update_sql = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in columns if c != "listing_id")

        sql = text(f"""
            INSERT INTO cars.listings ({col_sql})
            VALUES ({val_sql})
            ON CONFLICT (listing_id) DO UPDATE SET {update_sql}, scrape_date = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS inserted
        """)

        with self.engine.begin() as conn:
            row = conn.execute(sql, values).fetchone()
            inserted = bool(row[0]) if row else False

        self._mark_discovered_scraped(fixed_values.get("listing_id"))
        return inserted

    def _mark_discovered_scraped(self, listing_id) -> None:
        if not listing_id:
            return
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE cars.discovered_urls SET scraped = TRUE, "
                        "scraped_at = CURRENT_TIMESTAMP WHERE listing_id = :listing_id"
                    ),
                    {"listing_id": listing_id},
                )
        except Exception:
            # discovered_urls is an optional staging table (used only by the
            # two-phase full-crawl workflow) — deliberately a separate
            # transaction from the main upsert above, so a missing table here
            # can never roll back or fail the actual listing save.
            pass
