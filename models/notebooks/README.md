# notebooks

Not built yet. Exploratory analysis / EDA notebooks go here.

A couple of pointers for when you start:
- `data/processed/processed_listings_sample.csv` is a small (12-row)
  fully-featured sample you can load immediately without a database
  connection, for quickly testing notebook cells.
- To pull the real thing from Postgres:
  ```python
  import sys; sys.path.insert(0, "..")
  from src.db.database import get_engine, read_listings
  # or, for the already-processed table:
  import pandas as pd
  from config.settings import DATABASE_URL
  df = pd.read_sql("SELECT * FROM cars.processed_listings", DATABASE_URL)
  ```
- See `config/column_manifest.py` for which columns are safe to use
  as model features vs. analysis-only (price-derived, leakage risk).
