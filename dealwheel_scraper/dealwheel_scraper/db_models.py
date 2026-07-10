"""
Engine/session helpers and the ScrapeLog ORM model.

cars.listings is deliberately NOT modeled as a static declarative class here —
its feature_* columns are created dynamically at scrape time (see
feature_columns.py), so a fixed ORM mapping would drift out of sync with the
real table. PostgresPipeline talks to cars.listings with plain SQLAlchemy
Core/text() instead. cars.scrape_log has a fixed schema, so it gets a normal
declarative model.
"""
from __future__ import annotations

import os

from sqlalchemy import BigInteger, Column, Integer, Text, TIMESTAMP, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class ScrapeLog(Base):
    __tablename__ = "scrape_log"
    __table_args__ = {"schema": "cars"}

    id = Column(BigInteger, primary_key=True)
    scrape_start = Column(TIMESTAMP)
    scrape_end = Column(TIMESTAMP)
    ads_scraped = Column(Integer)
    new_ads = Column(Integer)
    updated_ads = Column(Integer)
    duration_seconds = Column(Integer)
    notes = Column(Text)


_engine = None


def get_engine():
    """Returns a process-wide singleton engine, built from DATABASE_URL."""
    global _engine
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to your .env file, e.g.\n"
                "DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dealwheel"
            )
        _engine = create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)
    return _engine


def insert_scrape_log(engine, *, scrape_start, scrape_end, ads_scraped, new_ads,
                       updated_ads, duration_seconds, notes) -> None:
    session = sessionmaker(bind=engine)()
    try:
        session.add(ScrapeLog(
            scrape_start=scrape_start,
            scrape_end=scrape_end,
            ads_scraped=ads_scraped,
            new_ads=new_ads,
            updated_ads=updated_ads,
            duration_seconds=duration_seconds,
            notes=notes,
        ))
        session.commit()
    finally:
        session.close()


def get_max_listing_id(engine) -> int:
    """Informational only (logged for visibility) — see the module docstring
    in spiders/pakwheels_incremental.py for why this isn't used to gate crawling."""
    with engine.connect() as conn:
        row = conn.execute(text("SELECT MAX(listing_id) FROM cars.listings")).fetchone()
        return row[0] if row and row[0] is not None else 0
