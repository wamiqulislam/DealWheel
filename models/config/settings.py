"""
config/settings.py

Loads environment variables (from .env, if present) and exposes:
    - Database connection settings
    - Tunable constants used by the feature-engineering modules

Every "assumption" the pipeline makes (average km driven per year,
which cities count as "large", the current-year reference point,
etc.) lives here so it's easy to find and adjust in one place instead
of being buried inside feature code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ============================================================
# Database connection
# ============================================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "cars")

# postgresql+psycopg2://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)


# ============================================================
# Feature-engineering constants (tunable assumptions)
# ============================================================

# Reference year used for car_age = reference_year - year.
# If a row has a scrape_date, the pipeline uses that row's scrape
# year instead (more correct when processing data scraped across
# multiple years). This is only the fallback for rows with no
# scrape_date.
FALLBACK_CURRENT_YEAR = int(os.getenv("FALLBACK_CURRENT_YEAR", "2026"))

# Assumed average kilometres driven per year in Pakistan, used to
# compute the "expected" mileage for a car of a given age
# (mileage_ratio = mileage / (car_age * AVERAGE_KM_PER_YEAR)).
# This is a genuine assumption -- adjust if you have better local data.
AVERAGE_KM_PER_YEAR = int(os.getenv("AVERAGE_KM_PER_YEAR", "12000"))

# is_new_car / is_very_old thresholds
NEW_CAR_MAX_AGE = 1
VERY_OLD_MIN_AGE = 15

# is_high_mileage / is_low_mileage thresholds (on mileage_ratio)
HIGH_MILEAGE_RATIO = 1.2
LOW_MILEAGE_RATIO = 0.8

# Year sanity bounds, mirrored from duplicates_impossibles.py so
# bucket edges stay consistent with what preprocessing already allows.
MIN_YEAR = 1950
MAX_YEAR = 2027
