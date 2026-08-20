"""
src/db/database.py

Thin PostgreSQL I/O layer around the cars.listings / cars.processed_listings
tables. Everything else in this project works on plain pandas
DataFrames -- this module is the only place that talks to the
database directly.

this module exists partly to protect against:
cars.processed_listings.listing_id is declared as
`REFERENCES cars.listings(id)` -- i.e. it is a foreign key to the
raw table's own auto-increment PRIMARY KEY (`listings.id`), NOT to
`listings.listing_id` (the external site's ad ID, which is also
just called "listing_id" on the raw side). Those are two different
numbers that happen to share a column name across the two tables.
read_listings() renames listings.id -> source_pk on the way in
specifically so it can't get silently confused with listings.listing_id
downstream; write_processed_listings() then writes source_pk into
processed_listings.listing_id.
"""

import pandas as pd
from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL, DB_SCHEMA


def get_engine(database_url=None):
    """Creates a SQLAlchemy engine. Call .dispose() on it when done, or use as a context manager."""
    return create_engine(database_url or DATABASE_URL)


def read_listings(engine, schema=DB_SCHEMA, limit=None):
    """
    Reads cars.listings in full. Returns a DataFrame with an extra
    `source_pk` column holding listings.id (renamed so it's never
    confused with listings.listing_id -- see module docstring).
    """
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    query = text(f"SELECT * FROM {schema}.listings {limit_clause}")

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if "id" not in df.columns:
        raise ValueError("cars.listings query did not return an `id` column -- check the schema.")

    df = df.rename(columns={"id": "source_pk"})
    print(f"[db] read {len(df):,} rows from {schema}.listings")
    return df


def write_processed_listings(df, engine, schema=DB_SCHEMA, mode="replace"):
    """
    Writes df to cars.processed_listings. df must already contain a
    `listing_id` column populated from listings.id (source_pk) --
    NOT from listings.listing_id.

    mode:
        "replace" (default) - TRUNCATE the table, then insert all
            rows fresh. Safe to re-run any number of times; always
            leaves processed_listings as an exact rebuild of the
            current listings + feature logic. Requires no schema
            change.
        "append" - plain INSERT, no dedup. Only safe for a table
            that starts empty, or if you've made sure `listing_id`
            can't repeat across runs yourself.
        "upsert" - INSERT ... ON CONFLICT (listing_id) DO UPDATE.
            Requires the unique constraint from
            sql/03_add_processed_listings_unique_constraint.sql.
    """
    if "listing_id" not in df.columns:
        raise ValueError(
            "write_processed_listings: df has no `listing_id` column. "
            "Populate it from listings.id (source_pk) before writing -- "
            "see src/pipeline/run_pipeline.py."
        )

    if mode == "replace":
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {schema}.processed_listings RESTART IDENTITY"))
            df.to_sql(
                "processed_listings",
                conn,
                schema=schema,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000,
            )
        print(f"[db] replaced {schema}.processed_listings with {len(df):,} rows")

    elif mode == "append":
        with engine.begin() as conn:
            df.to_sql(
                "processed_listings",
                conn,
                schema=schema,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000,
            )
        print(f"[db] appended {len(df):,} rows to {schema}.processed_listings")

    elif mode == "upsert":
        _upsert_processed_listings(df, engine, schema=schema)
        print(f"[db] upserted {len(df):,} rows into {schema}.processed_listings")

    else:
        raise ValueError(f"Unknown write mode: {mode!r} (expected replace/append/upsert)")


def _upsert_processed_listings(df, engine, schema=DB_SCHEMA):
    """
    INSERT ... ON CONFLICT (listing_id) DO UPDATE for every column
    except listing_id itself. Requires the unique constraint added by
    sql/03_add_processed_listings_unique_constraint.sql -- if it's
    missing, Postgres will raise, and the error message will say so.
    """
    columns = list(df.columns)
    update_columns = [c for c in columns if c != "listing_id"]

    insert_cols_sql = ", ".join(columns)
    insert_vals_sql = ", ".join(f":{c}" for c in columns)
    update_sql = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)

    stmt = text(
        f"""
        INSERT INTO {schema}.processed_listings ({insert_cols_sql})
        VALUES ({insert_vals_sql})
        ON CONFLICT (listing_id) DO UPDATE SET {update_sql}
        """
    )

    records = df.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(stmt, records)
