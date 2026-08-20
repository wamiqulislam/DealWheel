CREATE TABLE IF NOT EXISTS cars.scrape_log (
    id                  BIGSERIAL PRIMARY KEY,
    scrape_start        TIMESTAMP,
    scrape_end          TIMESTAMP,
    ads_scraped         INTEGER,
    new_ads             INTEGER,
    updated_ads         INTEGER,
    duration_seconds    INTEGER,
    notes               TEXT
);