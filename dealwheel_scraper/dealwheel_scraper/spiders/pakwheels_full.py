import scrapy

from .base_spider import BasePakWheelsSpider

# PakWheels' default sort (no explicit `sortby`) is "Updated Date: Recent
# First" (bumped_at-desc) — a "live" attribute that changes every time a
# seller renews/bumps their ad. On an actively-used marketplace that means
# the underlying list reorders WHILE a ~3100-page crawl is still running.
# model_year barely ever changes for a given ad, so sorting by it instead
# keeps the list far more stable — though not perfectly: ties within the
# same year are still reordered somewhat, which is the main reason a single
# combined pass (this spider) can undercount vs. the two-phase workflow
# (pakwheels_discover + pakwheels_scrape_urls), which is the recommended
# spider pair for a complete initial seed. This spider is kept for smaller
# or quicker runs where near-completeness is good enough.
SEARCH_URL = "https://www.pakwheels.com/used-cars/search/-/?sortby=model_year-desc"


class PakwheelsFullSpider(BasePakWheelsSpider):
    """
    One-pass full crawl: walks every page of the used-cars search results and
    visits every listing found in a single combined pass. Good for smaller
    or quicker runs; for the most complete initial seed of ~70k+ listings,
    use pakwheels_discover followed by pakwheels_scrape_urls instead, which
    isn't exposed to live reordering during the (slower) detail-scraping part
    of the crawl.

        scrapy crawl pakwheels_full
    """

    name = "pakwheels_full"

    def start_requests(self):
        yield scrapy.Request(SEARCH_URL, callback=self.parse, meta={"page": 1})

    def parse(self, response):
        requested_page = response.meta.get("page", 1)

        if self.check_page_redirect(response, requested_page):
            for href in response.css("a.car-name::attr(href)").getall():
                yield response.follow(href, callback=self.parse_listing, errback=self.handle_error)
            return

        ad_links = response.css("a.car-name::attr(href)").getall()

        if not ad_links:
            retry_request = self.retry_or_none(response)
            if retry_request:
                yield retry_request
                return
            # Retries exhausted for this specific page — move on rather than
            # getting stuck here forever. Already logged as an error above.
            next_url = self._next_page_url(response)
            yield response.follow(next_url, callback=self.parse, meta={"page": requested_page + 1})
            return

        self.note_page_had_listings(response)
        self.logger.info("Found %d listings on %s", len(ad_links), response.url)
        for href in ad_links:
            yield response.follow(href, callback=self.parse_listing, errback=self.handle_error)

        next_url = self._next_page_url(response)
        yield response.follow(next_url, callback=self.parse, meta={"page": requested_page + 1})
