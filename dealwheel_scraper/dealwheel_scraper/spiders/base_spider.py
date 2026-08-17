from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import scrapy

from ..extractors import extract_listing_data
from ..items import ListingItem


class BasePakWheelsSpider(scrapy.Spider):
    """Shared listing-page parsing, pagination, and error handling for all
    PakWheels crawlers."""

    allowed_domains = ["pakwheels.com"]

    _BLOCK_INDICATORS = (
        "captcha", "unusual traffic", "access denied",
        "verify you are human", "temporarily blocked", "rate limit",
    )

    # An empty search-result page is far more likely to be a transient
    # glitch (bot-throttle, or pagination drift on a live, actively-updated
    # site) than genuinely running out of results early — so we retry the
    # SAME page rather than moving on and silently losing whatever listings
    # were supposed to be there.
    MAX_PAGE_RETRIES = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_retry_counts: dict[str, int] = {}

    async def start(self):
        """Scrapy 2.13+ replaced the old synchronous start_requests() with
        this async generator — a spider that only defines start_requests()
        (as all of ours do) is silently given zero start requests instead,
        since the base Spider.start() only falls back to reading
        `start_urls` (which none of these spiders set). This bridges the
        two so every spider only needs to define start_requests() as before,
        regardless of which Scrapy version is actually installed."""
        for request in self.start_requests():
            yield request

    # ---- pagination helpers, shared by every spider that walks search pages ----

    @staticmethod
    def _page_number(url: str) -> int:
        """Reads the `page` query param off a URL (defaults to 1 if absent)."""
        query = parse_qs(urlparse(url).query)
        return int(query.get("page", ["1"])[0])

    @staticmethod
    def _next_page_url(response) -> str:
        """Increments the `page` query param on the current URL, preserving
        any other query params (e.g. sortby)."""
        parsed = urlparse(response.url)
        query = parse_qs(parsed.query)
        current_page = int(query.get("page", ["1"])[0])
        query["page"] = [str(current_page + 1)]
        new_query = urlencode({k: v[0] for k, v in query.items()})
        return urlunparse(parsed._replace(query=new_query))

    def check_page_redirect(self, response, requested_page: int) -> bool:
        """Returns True if this response landed on a different page than the
        one requested (i.e. PakWheels redirected us) — this is what caused
        the crawl to stop short of the true last page previously: computing
        "next page" from a redirected URL can loop back toward already-seen
        pages, which the dupefilter then silently swallows, starving the
        scheduler. Detecting it here lets the caller stop pagination
        cleanly instead."""
        actual_page = self._page_number(response.url)
        if actual_page != requested_page:
            self.logger.warning(
                "Requested page %d but landed on page %d instead (redirected) "
                "— likely hit PakWheels' own limit on how deep '?page=N' "
                "pagination goes. Recording/using whatever's on this page, "
                "then stopping pagination instead of looping.",
                requested_page, actual_page,
            )
            return True
        return False

    # ---- empty-page retry handling ----

    def retry_or_none(self, response):
        """Call when a search page yields zero listing links. Returns a
        Request that re-fetches the SAME page — with dont_filter=True, since
        Scrapy's default dupefilter would otherwise silently drop a repeat
        request to a URL already seen this run — or None once
        MAX_PAGE_RETRIES is exhausted for this specific page."""
        self.log_empty_page(response)
        retries = self._page_retry_counts.get(response.url, 0)

        if retries >= self.MAX_PAGE_RETRIES:
            self.logger.error(
                "Giving up on %s after %d empty retries — listings on this "
                "page may have been missed; search the log for this URL "
                "later if you want to re-check it manually.",
                response.url, self.MAX_PAGE_RETRIES,
            )
            return None

        self._page_retry_counts[response.url] = retries + 1
        self.logger.warning(
            "Retrying %s (attempt %d/%d) after an empty response.",
            response.url, retries + 1, self.MAX_PAGE_RETRIES,
        )
        return scrapy.Request(
            response.url,
            callback=self.parse,
            dont_filter=True,
            meta={**response.meta, "retry_multiplier": retries + 2},
        )

    def note_page_had_listings(self, response) -> None:
        self._page_retry_counts.pop(response.url, None)

    def log_empty_page(self, response):
        """Logs enough of the actual response to tell "genuinely no more
        results" apart from "got served a block/challenge page with a 200
        status" — neither of which show up as a clean stopping point otherwise."""
        body_snippet = response.text[:800]
        looks_blocked = any(marker in body_snippet.lower() for marker in self._BLOCK_INDICATORS)
        self.logger.warning(
            "No listings found on %s (HTTP %d)%s.\n--- body preview ---\n%s\n--- end preview ---",
            response.url,
            response.status,
            " — looks like a bot-block/challenge page" if looks_blocked else
            " — check the preview below: genuinely empty results, or a selector mismatch?",
            body_snippet,
        )

    # ---- listing detail page parsing (shared by every spider) ----

    def parse_listing(self, response):
        data = extract_listing_data(response)
        if not data.get("listing_id"):
            self.logger.warning("Could not determine listing_id for %s — skipping.", response.url)
            return
        yield ListingItem(**data)

    def handle_error(self, failure):
        self.logger.error("Request failed: %s (%r)", failure.request.url, failure.value)
