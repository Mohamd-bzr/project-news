"""TradingView webhook receiver.
Receives alert webhooks from TradingView and stores/sends them.

TradingView webhook payload (JSON):
{
    "secret": "your_webhook_secret",
    "strategy": "My Strategy",
    "ticker": "BTCUSDT",
    "action": "buy",
    "price": 65432.10,
    "message": "RSI oversold + support bounce"
}
"""

import os
import time
import json
import threading
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger('freebuff.tv_webhook')

ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "tv_alerts.json"
MAX_ALERTS = 500

# waitress serves with a thread pool, so two webhooks can land together:
# the read-append-write cycle and the file swap must not interleave.
_ALERTS_LOCK = threading.Lock()


def _load_alerts() -> List[Dict]:
    try:
        if ALERTS_PATH.exists():
            with open(ALERTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_alerts(alerts: List[Dict]):
    """Atomic write: a crash mid-save must not truncate the alert file."""
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ALERTS_PATH.with_suffix(".json.tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(alerts[-MAX_ALERTS:], f, ensure_ascii=False, indent=2)
    os.replace(tmp, ALERTS_PATH)


def _strip_secret(alert: Dict) -> Dict:
    """The webhook secret must never be persisted or served back — /api/alerts
    is open by design, so a stored secret there would publish the one
    credential protecting /webhook/tv. Legacy files are scrubbed on load."""
    raw = alert.get("raw")
    if isinstance(raw, dict) and "secret" in raw:
        raw = {k: v for k, v in raw.items() if k != "secret"}
        alert = dict(alert)
        alert["raw"] = raw
    return alert


def process_webhook(payload: Dict, secret: str) -> Dict:
    """Process a TradingView webhook payload.

    Returns:
        {'ok': True, 'alert_id': int, 'message': str} or
        {'ok': False, 'error': str}
    """
    # Validate secret
    if not secret or payload.get('secret') != secret:
        return {'ok': False, 'error': 'invalid secret'}

    alert = {
        'id': int(time.time() * 1000),
        'timestamp': time.time(),
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': payload.get('strategy', 'Unknown'),
        'ticker': payload.get('ticker', 'Unknown'),
        'action': payload.get('action', 'unknown'),
        'price': payload.get('price'),
        'message': payload.get('message', ''),
        # stored without the secret field — see _strip_secret
        'raw': {k: v for k, v in payload.items() if k != 'secret'},
    }

    with _ALERTS_LOCK:
        alerts = _load_alerts()
        alerts.append(alert)
        _save_alerts(alerts)

    logger.info(f"TV Alert: {alert['strategy']} -> {alert['ticker']} {alert['action']} @ {alert['price']}")

    return {
        'ok': True,
        'alert_id': alert['id'],
        'message': f"Alert recorded: {alert['ticker']} {alert['action']}",
    }


def get_recent_alerts(limit: int = 20) -> List[Dict]:
    """Get recent TradingView alerts (secret-free; legacy rows scrubbed)."""
    with _ALERTS_LOCK:
        alerts = _load_alerts()
        clean = [_strip_secret(a) for a in alerts]
        if clean != alerts:               # legacy file carried secrets: rewrite it
            _save_alerts(clean)
        return clean[-limit:]


def get_alerts_for_ticker(ticker: str, limit: int = 20) -> List[Dict]:
    """Get alerts for a specific ticker (secret-free)."""
    with _ALERTS_LOCK:
        alerts = [_strip_secret(a) for a in _load_alerts()]
    filtered = [a for a in alerts if a.get('ticker', '').upper() == ticker.upper()]
    return filtered[-limit:]
