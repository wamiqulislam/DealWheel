"""
Phase 2 of the two-phase full crawl: reads every URL recorded by
pakwheels_discover (cars.discovered_urls) and scrapes each one exactly once.
Doesn't touch the search-index pages at all, so live reordering on
PakWheels' side (sellers renewing/editing ads) can't cause listings to be
missed here — the list of what to fetch was already fixed by phase 1, before
this (slower, ~70k-request) phase even started.

Only fetches rows not yet marked scraped (PostgresPipeline marks a row
scraped once its listing is successfully upserted), so an interrupted run
can simply be re-run to pick up where it left off, and a stragglers-only
follow-up run costs almost nothing once most rows are already done.

    scrapy crawl pakwheels_scrape_urls
"""
import scrapy
from sqlalchemy import text

from ..db_models import get_engine
from .base_spider import BasePakWheelsSpider


class PakwheelsScrapeUrlsSpider(BasePakWheelsSpider):
    name = "pakwheels_scrape_urls"

    def start_requests(self):
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT ad_url FROM cars.discovered_urls WHERE scraped = FALSE")
            ).fetchall()
        self.logger.info("Loaded %d not-yet-scraped URL(s) from cars.discovered_urls.", len(rows))
        for row in rows:
            yield scrapy.Request(row[0], callback=self.parse_listing, errback=self.handle_error)
