-- ============================================================
-- OPTIONAL migration.
--
-- The base processed_listings schema has no UNIQUE constraint on
-- listing_id, so re-running the pipeline in "append" write-mode
-- will create duplicate rows for the same source listing.
--
-- The pipeline's default write-mode ("replace") avoids this by
-- truncating and rebuilding the whole table every run, so you do
-- NOT need this migration to use the pipeline safely.
--
-- Run this only if you want to use --write-mode upsert instead
-- (e.g. for incremental/streaming ingestion where rebuilding the
-- full table every run is too slow).
-- ============================================================

ALTER TABLE cars.processed_listings
    ADD CONSTRAINT uq_processed_listings_listing_id UNIQUE (listing_id);
