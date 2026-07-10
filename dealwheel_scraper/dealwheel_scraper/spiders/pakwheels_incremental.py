import scrapy

from ..db_models import get_engine, get_max_listing_id
from .base_spider import BasePakWheelsSpider
from .pakwheels_full import PakwheelsFullSpider

# PakWheels' own search UI only exposes sorting by *last update* ("bumped_at"),
# price, model year, or mileage — there's no "date posted"/listing-ID sort
# (confirmed from the live <select id="sortby"> options: bumped_at-desc/asc,
# price-asc/desc, model_year-desc/asc, mileage-asc/desc). That means a
# recently-renewed OLD listing can appear ahead of a genuinely new one in this
# feed, so we can't just stop at the first already-known listing_id the way a
# simple "sorted by newest ID" feed would let us.
#
# Instead: PostgresPipeline tracks how many *consecutive* items in a row it
# upserted as "already existed" (via duplicate_stop_threshold below) and
# raises CloseSpider once that streak is long enough — meaning we've run past
# today's freshly-touched listings. MAX_PAGES is a hard cap in case that
# signal never fires (e.g. almost everything on the site got bumped somehow).
INCREMENTAL_SEARCH_URL = "https://www.pakwheels.com/used-cars/search/-/?sortby=bumped_at-desc"


class PakwheelsIncrementalSpider(BasePakWheelsSpider):
    """
    Daily incremental crawl — see module docstring above for the stopping
    strategy, which is deliberately NOT a strict listing_id cutoff.

        scrapy crawl pakwheels_incremental
    """

    name = "pakwheels_incremental"

    # Read by PostgresPipeline: stop once this many consecutive items already
    # existed in the DB (~2 pages of nothing new). Left unset on
    # PakwheelsFullSpider, which should never stop early like this.
    duplicate_stop_threshold = 50

    MAX_PAGES = 400  # hard safety cap (~10k listings) regardless of the signal above

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Informational only — logged for visibility, NOT used to gate
        # scraping, since bumped_at order doesn't reliably correlate with
        # listing_id (see module docstring).
        try:
            max_id = get_max_listing_id(get_engine())
            self.logger.info("Incremental crawl starting; max known listing_id=%s", max_id)
        except Exception:
            self.logger.exception("Could not read max listing_id (continuing anyway).")

    def start_requests(self):
        yield scrapy.Request(INCREMENTAL_SEARCH_URL, meta={"page": 1}, callback=self.parse)

    def parse(self, response):
        page = response.meta.get("page", 1)
        ad_links = response.css("a.car-name::attr(href)").getall()
        if not ad_links:
            self.logger.info("No listings found on %s — stopping.", response.url)
            return

        for href in ad_links:
            yield response.follow(href, callback=self.parse_listing, errback=self.handle_error)

        if page >= self.MAX_PAGES:
            self.logger.info("Hit MAX_PAGES=%d safety cap — stopping.", self.MAX_PAGES)
            return

        next_url = PakwheelsFullSpider._next_page_url(response)
        if next_url:
            yield response.follow(next_url, callback=self.parse, meta={"page": page + 1})
