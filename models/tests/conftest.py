"""
tests/conftest.py

Mirrors the sys.path setup in src/pipeline/run_pipeline.py so tests
can import src/preprocessing/*.py and src/features/*.py using the
same plain sibling-import style those modules use internally.
See the comment at the top of run_pipeline.py for why this is
necessary (short version: src/preprocessing was supplied as-is with
bare imports, so its directory must be on sys.path directly).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
PREPROCESSING_DIR = SRC_DIR / "preprocessing"
FEATURES_DIR = SRC_DIR / "features"

for path in (PROJECT_ROOT, SRC_DIR, PREPROCESSING_DIR, FEATURES_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture
def raw_columns():
    from config.column_manifest import RAW_LISTINGS_COLUMNS

    return RAW_LISTINGS_COLUMNS
