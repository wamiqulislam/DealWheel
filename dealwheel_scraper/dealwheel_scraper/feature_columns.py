"""
Manages the dynamic feature_* columns on cars.listings.

PakWheels ads list a variable set of tick-box features ("Air Conditioning",
"Power Steering", "ABS", ...). Per spec, each distinct feature becomes its own
SMALLINT column (1 = present, 0 = absent), added on the fly the first time
it's seen, with existing rows defaulting to 0 for any column that didn't exist
yet when they were inserted.

Note: this can grow the table wide if PakWheels' feature vocabulary is large
or inconsistently worded (e.g. "AC" vs "Air Conditioning" would become two
columns). In practice the feature list on this site is a fairly small, fixed
vocabulary, so this stays bounded — but if you'd rather have a single
`extra_specs JSONB` catch-all column instead of one column per feature, that's
a reasonable alternative worth considering later.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .cleaning import slugify_feature

logger = logging.getLogger(__name__)


class FeatureColumnManager:
    def __init__(self, engine: Engine, schema: str = "cars", table: str = "listings"):
        self.engine = engine
        self.schema = schema
        self.table = table
        self._known_columns: set[str] = set()
        self._load_existing_columns()

    def _load_existing_columns(self) -> None:
        query = text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table"
        )
        with self.engine.connect() as conn:
            rows = conn.execute(query, {"schema": self.schema, "table": self.table})
            self._known_columns = {row[0] for row in rows}

    def ensure_columns(self, feature_names) -> set[str]:
        """Ensures a DB column exists for each feature name seen.
        Returns the set of column slugs present in THIS call (for building the row)."""
        present = set()
        for name in feature_names:
            if not name:
                continue
            slug = slugify_feature(name)
            present.add(slug)
            if slug not in self._known_columns:
                self._add_column(slug)
        return present

    def _add_column(self, slug: str) -> None:
        # slug is produced by slugify_feature, which only ever emits [a-z0-9_],
        # so this is safe from injection even though it's built with an f-string.
        ddl = text(f'ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS "{slug}" SMALLINT DEFAULT 0')
        with self.engine.begin() as conn:
            conn.execute(ddl)
        self._known_columns.add(slug)
        logger.info("Added new feature column: %s.%s.%s", self.schema, self.table, slug)

    @property
    def known_feature_columns(self) -> set[str]:
        return {c for c in self._known_columns if c.startswith("feat_")}
