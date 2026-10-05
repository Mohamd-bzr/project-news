"""Middleware for feature gating.
Wraps Flask endpoints with tier checks.
"""

import time
import hashlib
from functools import wraps
from flask import request, jsonify


def _get_daily_usage(api_key: str, feature: str) -> int:
    """Get daily usage count for a feature."""
    from billing import _get_conn, _lock
    
    if not api_key:
        return 0
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT id FROM users WHERE api_key_hash = ?", (key_hash,)).fetchone()
            if not row:
                return 0
            
            today_start = time.strftime('%Y-%m-%d 00:00:00')
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
            from billing import check_feature, track_usage, get_user_tier
            
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            # Check if it's a daily limit feature
            if feature == "ai_summaries_daily":
                user = get_user_tier(api_key)
                daily_limit = user.get('features', {}).get('ai_summaries_daily', 3)
                daily_used = _get_daily_usage(api_key, 'ai_summaries_daily')
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
