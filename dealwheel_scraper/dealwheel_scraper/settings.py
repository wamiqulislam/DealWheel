import os

from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "dealwheel_scraper"
SPIDER_MODULES = ["dealwheel_scraper.spiders"]
NEWSPIDER_MODULE = "dealwheel_scraper.spiders"

# I couldn't confirm what pakwheels.com/robots.txt currently allows from here —
# check it yourself and flip this to True if you'd rather Scrapy respect it.
# (Your old requests+BeautifulSoup scraper didn't check it either.)
ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = int(os.getenv("SCRAPY_CONCURRENT_REQUESTS", "16"))
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("SCRAPY_CONCURRENT_REQUESTS", "16"))

# Actual per-request delay is handled by RandomDelayMiddleware below, so Scrapy's
# own delay is off to avoid stacking both.
DOWNLOAD_DELAY = 0
RANDOM_DELAY_MIN = float(os.getenv("RANDOM_DELAY_MIN", "1.8"))
RANDOM_DELAY_MAX = float(os.getenv("RANDOM_DELAY_MAX", "3.7"))

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
# AUTOTHROTTLE_DEBUG = True  # uncomment to see throttling decisions in the log

RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]

COOKIES_ENABLED = True

PROXY_URL = os.getenv("PROXY_URL")  # optional; leave unset in .env to disable

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "dealwheel_scraper.middlewares.RandomUserAgentMiddleware": 400,
    "dealwheel_scraper.middlewares.ProxyMiddleware": 410,
    "dealwheel_scraper.middlewares.RandomDelayMiddleware": 420,
    # High priority number -> its process_response runs early on the way back,
    # ahead of Scrapy's built-in RetryMiddleware (default priority 550).
    "dealwheel_scraper.middlewares.BlockDetectionMiddleware": 830,
}

ITEM_PIPELINES = {
    "dealwheel_scraper.pipelines.ValidationPipeline": 100,
    "dealwheel_scraper.pipelines.CleaningPipeline": 200,
    "dealwheel_scraper.pipelines.PostgresPipeline": 300,
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/dealwheel_scraper.log")
if LOG_FILE:
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

FEED_EXPORT_ENCODING = "utf-8"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
