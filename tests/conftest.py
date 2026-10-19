"""Shared fixtures for the test suite.

The test suite runs hermetically:
- An autouse, session-level fixture copies settings.json and the DB schema to a tmp
  dir BEFORE importing app or database, sets MOHMD_CONFIG, MOHMD_DB, and MOHMD_NO_BACKGROUND=1,
  and asserts at teardown that the sha256 of the real settings.json did not change.
"""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEBUFF_ROOT = Path(r"e:\freebuff")

REAL_SETTINGS = (FREEBUFF_ROOT / "settings.json") if (FREEBUFF_ROOT / "settings.json").exists() else (REPO_ROOT / "settings.json")


def _hash_file(p: Path) -> str:
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


# Prepare the hermetic temporary directory at module import time
# BEFORE any test module imports app or database.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="mohmd_hermetic_"))
_TMP_CONFIG = _TMP_DIR / "settings.json"
_TMP_DB = _TMP_DIR / ".mohmd_news.db"

if REAL_SETTINGS.exists():
    shutil.copy2(REAL_SETTINGS, _TMP_CONFIG)
else:
    _TMP_CONFIG.write_text("{}", encoding="utf-8")

os.environ["MOHMD_CONFIG"] = str(_TMP_CONFIG)
os.environ["MOHMD_DB"] = str(_TMP_DB)
os.environ["MOHMD_NO_BACKGROUND"] = "1"


@pytest.fixture(scope="session", autouse=True)
def _hermetic_test_env():
    initial_settings_hash = _hash_file(REAL_SETTINGS)

    # Initialize the temporary database schema
    import database
    database.init_db()

    yield

    # Teardown assertion: verify real settings.json was not modified
    final_settings_hash = _hash_file(REAL_SETTINGS)
    assert final_settings_hash == initial_settings_hash, (
        f"Real settings.json was modified during test run! "
        f"path={REAL_SETTINGS} initial={initial_settings_hash} final={final_settings_hash}"
    )

    # Clean up temp directory
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
