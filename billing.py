"""Freemium tier management for FreeBuff.
Handles tier checks, feature gating, and usage tracking.

Storage: SQLite database (freebuff_tiers.db)
"""

import sqlite3
import time
import hashlib
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "freebuff_tiers.db"
_lock = threading.Lock()


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_tier_db():
    """Initialize tier database schema."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                api_key_hash TEXT UNIQUE,
                tier TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                alerts_used INTEGER DEFAULT 0,
                alerts_limit INTEGER DEFAULT 3,
                api_requests_today INTEGER DEFAULT 0,
                api_limit INTEGER DEFAULT 100,
                api_reset_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                feature TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        conn.commit()
    finally:
        conn.close()


# Tier definitions
TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'api_limit': 100,
        'alerts_limit': 3,
        'data_retention_days': 7,
        'features': {
            'dashboard': True,
            'basic_indicators': True,
            'sentiment_basic': True,
            'charts_1d': True,
            'ai_summaries_daily': 3,
            'ai_predictions': False,
            'custom_alerts': 3,
            'export': False,
            'email_digest': False,
            'discord': False,
            'priority_scraping': False,
            'advanced_charts': False,
        },
    },
    'pro': {
        'name': 'Pro',
        'price': 9,
        'api_limit': 1000,
        'alerts_limit': 999,
        'data_retention_days': 90,
        'features': {
            'dashboard': True,
            'basic_indicators': True,
            'sentiment_basic': True,
            'sentiment_advanced': True,
            'sentiment_history': True,
            'charts_1d': True,
            'charts_all_timeframes': True,
            'ai_summaries_daily': 999,
            'ai_predictions': True,
            'custom_alerts': 999,
            'export': True,
            'email_digest': True,
            'discord': True,
            'priority_scraping': True,
            'advanced_charts': True,
        },
    },
}


def _is_expired(value) -> bool:
    """True when a stored expiry has passed. Accepts epoch, numeric text,
    ISO-8601 (with or without a zone) and SQLite's 'YYYY-MM-DD HH:MM:SS'.

    An unparseable value is treated as *not* expired rather than as an error:
    a corrupt timestamp must not silently downgrade a paying subscriber.
    """
    if value in (None, ""):
        return False
    if isinstance(value, (int, float)):
        return time.time() > float(value)
    text = str(value).strip()
    if not text:
        return False
    try:
        return time.time() > float(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.now(timezone.utc) > datetime.strptime(text, fmt).replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > dt
    except ValueError:
        return False


def get_user_tier(api_key: str) -> Dict:
    """Get user tier and limits from API key.

    No hardcoded master keys: a constant in source is public the moment the
    repo ships. The dashboard's own caller uses the randomly-generated key
    persisted in data/api_keys.json like everyone else.
    """
    if not api_key:
        return {'tier': 'free', **TIERS['free']}

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE api_key_hash = ?", (key_hash,)).fetchone()
            if row:
                tier_name = row['tier']
                tier_config = TIERS.get(tier_name, TIERS['free'])
                
                # Check expiry. `expires_at` is a TEXT column, so comparing it
                # to time.time() (a float) raised TypeError the moment an
                # expiry was actually set — which is why nothing set one.
                if _is_expired(row['expires_at']):
                    tier_name = 'free'
                    tier_config = TIERS['free']
                
                return {
                    'tier': tier_name,
                    'user_id': row['id'],
                    'email': row['email'],
                    'api_limit': tier_config['api_limit'],
                    'alerts_limit': tier_config['alerts_limit'],
                    'features': tier_config['features'],
                }
        finally:
            conn.close()
    
    return {'tier': 'free', **TIERS['free']}


def check_feature(api_key: str, feature: str):
    """Check if a user has access to a feature."""
    user = get_user_tier(api_key)
    return user.get('features', {}).get(feature, False)


def track_usage(api_key: str, feature: str):
    """Track feature usage."""
    if not api_key:
        return
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT id FROM users WHERE api_key_hash = ?", (key_hash,)).fetchone()
            if row:
                conn.execute(
                    "INSERT INTO usage_log (user_id, feature) VALUES (?, ?)",
                    (row['id'], feature)
                )
                conn.commit()
        finally:
            conn.close()


def register_user(email: str, api_key: str, tier: str = 'free') -> Dict:
    """Register a new user."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO users (email, api_key_hash, tier) VALUES (?, ?, ?)",
                (email, key_hash, tier)
            )
            conn.commit()
            return {'ok': True, 'email': email, 'tier': tier}
        except sqlite3.IntegrityError:
            return {'ok': False, 'error': 'email already registered'}
        finally:
            conn.close()


# Initialize on import
init_tier_db()
