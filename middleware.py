"""Middleware for feature gating.
Wraps Flask endpoints with tier checks.
"""

import time
import hashlib
import threading
from datetime import datetime, timezone
from functools import wraps
from flask import request, jsonify


def _utc_day_start() -> str:
    """SQLite's CURRENT_TIMESTAMP is UTC — compare it against a UTC day
    start, not local time, or the daily window shifts by the server's
    timezone offset (this box runs +3:30)."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d 00:00:00')


# Anonymous / unknown-key callers have no users row to count against, but
# they must still be rate-limited or the free tier's daily cap is a no-op.
# In-memory per-day counters: a limiter may reset on restart, billing may not.
_ANON_USAGE = {}
_ANON_LOCK = threading.Lock()


def _anon_count_and_track(ident: str, limit: int) -> int:
    """Count this caller's use for today; returns the post-use count."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    with _ANON_LOCK:
        rec = _ANON_USAGE.get(ident)
        if not rec or rec.get("day") != today:
            rec = {"day": today, "n": 0}
            _ANON_USAGE[ident] = rec
        rec["n"] += 1
        return rec["n"]


def _get_daily_usage(api_key: str, feature: str):
    """Get daily usage count for a feature; None when the key has no row."""
    from billing import _get_conn, _lock

    if not api_key:
        return None

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]

    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT id FROM users WHERE api_key_hash = ?", (key_hash,)).fetchone()
            if not row:
                return None

            today_start = _utc_day_start()
            count = conn.execute(
                "SELECT COUNT(*) FROM usage_log WHERE user_id = ? AND feature = ? AND timestamp >= ?",
                (row['id'], feature, today_start)
            ).fetchone()[0]
            return count
        finally:
            conn.close()


def require_tier(feature: str):
    """Decorator: requires a specific feature from the user's tier.

    Usage:
        @app.route("/api/ai/summary/<symbol>")
        @require_tier("ai_summaries_daily")
        def api_ai_summary(symbol): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from billing import check_feature, track_usage, get_user_tier, TIERS

            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

            # Check if it's a daily limit feature
            if feature == "ai_summaries_daily":
                user = get_user_tier(api_key)
                daily_limit = user.get('features', {}).get('ai_summaries_daily', 3)
                daily_used = _get_daily_usage(api_key, 'ai_summaries_daily')
                if daily_used is None:
                    # no users row (anonymous or unknown key): count against a
                    # per-caller limiter keyed by IP / key material — the free
                    # cap used to be a no-op for exactly these callers
                    ident = (request.remote_addr or "unknown") if not api_key \
                        else "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:16]
                    free_limit = TIERS.get('free', {}).get('features', {}).get(feature, 3)
                    used = _anon_count_and_track(ident, free_limit)
                    if used > free_limit:
                        return jsonify({
                            "error": "Feature limit reached",
                            "feature": feature,
                            "used": used,
                            "limit": free_limit,
                            "upgrade": "Get Pro for unlimited access: /api/billing/upgrade"
                        }), 403
                    return f(*args, **kwargs)
                if daily_used >= daily_limit:
                    return jsonify({
                        "error": "Feature limit reached",
                        "feature": feature,
                        "used": daily_used,
                        "limit": daily_limit,
                        "upgrade": "Get Pro for unlimited access: /api/billing/upgrade"
                    }), 403

                track_usage(api_key, feature)
                return f(*args, **kwargs)

            tier_info = check_feature(api_key, feature)

            if not tier_info:
                return jsonify({
                    "error": "Feature not available on your tier",
                    "feature": feature,
                    "current_tier": get_user_tier(api_key).get('tier', 'free'),
                    "upgrade": "Upgrade to Pro: /api/billing/upgrade"
                }), 403

            track_usage(api_key, feature)
            return f(*args, **kwargs)
        return decorated
    return decorator
