"""
Phase 1 of the two-phase full crawl: walks every search-results page and
records every listing URL it finds into cars.discovered_urls — WITHOUT
visiting any listing detail pages. This deliberately only touches the much
smaller set of search-index pages (~3100) rather than the ~70k+ detail
pages, so it finishes far faster than a combined crawl. That matters because
PakWheels' feed reorders live as sellers renew/edit ads: the shorter this
phase takes, the less the site can reshuffle underneath it, and the more
complete the discovered URL list ends up being.

Run this first, then run pakwheels_scrape_urls to actually fetch and store
each discovered listing — see that spider's docstring for why splitting it
out this way avoids the undercounting a single combined pass is prone to.

    scrapy crawl pakwheels_discover
"""
import scrapy
from sqlalchemy import text

from ..db_models import get_engine
from ..extractors import extract_listing_id
from .base_spider import BasePakWheelsSpider
from .pakwheels_full import SEARCH_URL


class PakwheelsDiscoverSpider(BasePakWheelsSpider):
    name = "pakwheels_discover"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = get_engine()
        self._discovered_count = 0

    def start_requests(self):
        yield scrapy.Request(SEARCH_URL, callback=self.parse, meta={"page": 1})

    def parse(self, response):
        requested_page = response.meta.get("page", 1)

        if self.check_page_redirect(response, requested_page):
            self._save_links(response)
            return

        ad_links = response.css("a.car-name::attr(href)").getall()

        if not ad_links:
            retry_request = self.retry_or_none(response)
            if retry_request:
                yield retry_request
                return
            next_url = self._next_page_url(response)
            yield response.follow(next_url, callback=self.parse, meta={"page": requested_page + 1})
            return

        self.note_page_had_listings(response)
        self._save_links(response)

        next_url = self._next_page_url(response)
        yield response.follow(next_url, callback=self.parse, meta={"page": requested_page + 1})

    def _save_links(self, response) -> None:
        for href in response.css("a.car-name::attr(href)").getall():
            url = response.urljoin(href)
            listing_id = extract_listing_id(url)
            if not listing_id:
                continue
            try:
                with self.engine.begin() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO cars.discovered_urls (listing_id, ad_url) "
                            "VALUES (:listing_id, :ad_url) "
                            "ON CONFLICT (listing_id) DO NOTHING"
                        ),
                        {"listing_id": listing_id, "ad_url": url},
                    )
                self._discovered_count += 1
            except Exception:
                self.logger.exception("Failed to save discovered URL %s", url)
        self.logger.info("Discovered %d listing URLs so far (this response: %s).",
                          self._discovered_count, response.url)

    def closed(self, reason):
        self.logger.info("Discovery finished: %d listing URLs recorded (reason=%s).",
                          self._discovered_count, reason)
        if self.engine:
            self.engine.dispose()
