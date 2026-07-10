"""
Downloader middlewares: realistic UA rotation, optional proxy, a random
human-scale delay, and basic blocking detection.

RandomDelayMiddleware deliberately does NOT time.sleep() — that would block
the whole Twisted reactor (and every other in-flight request) for the entire
delay. Scheduling the delay via reactor.callLater and returning a Deferred
achieves a per-request random delay without stalling concurrent requests.
"""
from __future__ import annotations

import random

from scrapy.exceptions import CloseSpider
from twisted.internet import defer, reactor

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
# NOTE: this list will inevitably drift stale as browsers ship new versions —
# refresh it occasionally (e.g. from whatismybrowser.com/guides/the-latest-user-agent).


class RandomUserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(USER_AGENTS)


class ProxyMiddleware:
    """No-op unless PROXY_URL is set in the environment/.env — see .env.example."""

    def __init__(self, proxy_url):
        self.proxy_url = proxy_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("PROXY_URL"))

    def process_request(self, request, spider):
        if self.proxy_url:
            request.meta["proxy"] = self.proxy_url


class RandomDelayMiddleware:
    """Adds a random, non-blocking delay in [RANDOM_DELAY_MIN, RANDOM_DELAY_MAX]
    seconds before each request goes out."""

    def __init__(self, min_delay, max_delay):
        self.min_delay = min_delay
        self.max_delay = max_delay

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler.settings.getfloat("RANDOM_DELAY_MIN", 1.8),
            crawler.settings.getfloat("RANDOM_DELAY_MAX", 3.7),
        )

    def process_request(self, request, spider):
        delay = random.uniform(self.min_delay, self.max_delay)
        d = defer.Deferred()
        reactor.callLater(delay, d.callback, None)
        return d


class BlockDetectionMiddleware:
    """Tracks consecutive block-like responses (403/429) and closes the spider
    if too many happen in a row, rather than hammering a server that's clearly
    turning us away. This is deliberately simple — no CAPTCHA handling, no
    stealth tricks, just "stop and let a human look at it"."""

    BLOCK_STATUS_CODES = {403, 429}
    MAX_CONSECUTIVE_BLOCKS = 5

    def __init__(self):
        self.consecutive_blocks = 0

    def process_response(self, request, response, spider):
        if response.status in self.BLOCK_STATUS_CODES:
            self.consecutive_blocks += 1
            spider.logger.warning(
                "Possible blocking: status %d on %s (streak=%d)",
                response.status, request.url, self.consecutive_blocks,
            )
            if self.consecutive_blocks >= self.MAX_CONSECUTIVE_BLOCKS:
                raise CloseSpider(
                    f"Stopped: {self.consecutive_blocks} consecutive {response.status} responses — "
                    "likely blocked, needs manual investigation."
                )
        else:
            self.consecutive_blocks = 0
        return response
