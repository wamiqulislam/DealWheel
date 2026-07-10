import scrapy

from ..extractors import extract_listing_data
from ..items import ListingItem


class BasePakWheelsSpider(scrapy.Spider):
    """Shared listing-page parsing + error handling for both the full and
    incremental crawlers. Each subclass only needs to implement its own
    `parse` (how to walk search result pages) and `start_requests`."""

    allowed_domains = ["pakwheels.com"]

    def parse_listing(self, response):
        data = extract_listing_data(response)
        if not data.get("listing_id"):
            self.logger.warning("Could not determine listing_id for %s — skipping.", response.url)
            return
        yield ListingItem(**data)

    def handle_error(self, failure):
        self.logger.error("Request failed: %s (%r)", failure.request.url, failure.value)
