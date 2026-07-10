from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .base_spider import BasePakWheelsSpider

SEARCH_URL = "https://www.pakwheels.com/used-cars/search/-/"


class PakwheelsFullSpider(BasePakWheelsSpider):
    """
    One-time full crawl: walks every page of the used-cars search results and
    visits every listing found. Meant to be run once to seed the database
    (~70k listings) — use pakwheels_incremental for ongoing daily updates.

        scrapy crawl pakwheels_full
    """

    name = "pakwheels_full"
    start_urls = [SEARCH_URL]

    def parse(self, response):
        ad_links = response.css("a.car-name::attr(href)").getall()
        if not ad_links:
            self.logger.info("No listings found on %s — stopping full crawl.", response.url)
            return

        self.logger.info("Found %d listings on %s", len(ad_links), response.url)
        for href in ad_links:
            yield response.follow(href, callback=self.parse_listing, errback=self.handle_error)

        next_url = self._next_page_url(response)
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    @staticmethod
    def _next_page_url(response) -> str | None:
        """Increments the `page` query param on the current URL. Used by both
        spiders (the incremental one imports this to stay in sync)."""
        parsed = urlparse(response.url)
        query = parse_qs(parsed.query)
        current_page = int(query.get("page", ["1"])[0])
        query["page"] = [str(current_page + 1)]
        new_query = urlencode({k: v[0] for k, v in query.items()})
        return urlunparse(parsed._replace(query=new_query))
