"""Shared fixtures for the test suite.

The test suite runs hermetically:
- An autouse, session-level fixture copies settings.json (with all secrets blanked)
  and the DB schema to a tmp dir BEFORE importing app or database, sets MOHMD_CONFIG,
  MOHMD_DB, and MOHMD_NO_BACKGROUND=1, and asserts at teardown that the sha256 of the
  real settings.json did not change.
- A session-wide requests safety net raises AssertionError on any HTTP request to a
  non-local host unless explicitly patched.
"""

import hashlib
import json
import os
import shutil
import tempfile
import urllib.parse
from pathlib import Path
import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEBUFF_ROOT = Path(r"e:\freebuff")

REAL_SETTINGS = (FREEBUFF_ROOT / "settings.json") if (FREEBUFF_ROOT / "settings.json").exists() else (REPO_ROOT / "settings.json")


def _hash_file(p: Path) -> str:
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sanitize_config(obj):
    """Strip real credentials and channels while keeping config schema."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            k_low = k.lower()
            if k == "telegram_channels":
                res[k] = []
            elif k == "tv_webhook_secret":
                res[k] = "test-tv-secret"
            elif k in ("token", "proxy", "api_key", "youtube_key", "instagram_token",
                       "instagram_user_id", "openai_key", "webhook_url") or \
                 any(sec in k_low for sec in ["secret", "password"]):
                res[k] = ""
            elif k in ("chat", "channel_id"):
                res[k] = "" if isinstance(v, str) else 0
            elif isinstance(v, (dict, list)):
                res[k] = _sanitize_config(v)
            else:
                res[k] = v
        return res
    elif isinstance(obj, list):
        return [_sanitize_config(x) for x in obj]
    return obj


# Prepare the hermetic temporary directory at module import time
# BEFORE any test module imports app or database.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="mohmd_hermetic_"))
_TMP_CONFIG = _TMP_DIR / "settings.json"
_TMP_DB = _TMP_DIR / ".mohmd_news.db"

if REAL_SETTINGS.exists():
    raw_cfg = json.loads(REAL_SETTINGS.read_text(encoding="utf-8"))
    sanitized_cfg = _sanitize_config(raw_cfg)
    _TMP_CONFIG.write_text(json.dumps(sanitized_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
else:
    _TMP_CONFIG.write_text("{}", encoding="utf-8")

os.environ["MOHMD_CONFIG"] = str(_TMP_CONFIG)
os.environ["MOHMD_DB"] = str(_TMP_DB)
os.environ["MOHMD_NO_BACKGROUND"] = "1"

# Session-wide requests guard
_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
_orig_session_send = requests.Session.send


def _guarded_send(self, request, **kwargs):
    parsed = urllib.parse.urlparse(request.url)
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise AssertionError(f"real network in tests: blocked request to {request.url}")
    return _orig_session_send(self, request, **kwargs)


requests.Session.send = _guarded_send


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
