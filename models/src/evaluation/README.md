# src/evaluation

Not built yet. This is where evaluation/reporting code will live once
a model exists in `src/training` -- metrics, error analysis,
residual plots, comparisons against a naive baseline, etc.

`cars.processed_listings` already carries `market_avg_price` /
`market_price_ratio` / `percent_below_market` (analysis-only, see the
root README) which are natural candidates for slicing model error by
"how far off was this listing from its market segment".
