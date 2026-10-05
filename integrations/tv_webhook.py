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

import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('freebuff.tv_webhook')

ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "tv_alerts.json"
MAX_ALERTS = 500


def _load_alerts() -> List[Dict]:
    try:
        if ALERTS_PATH.exists():
            with open(ALERTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_alerts(alerts: List[Dict]):
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(alerts[-MAX_ALERTS:], f, ensure_ascii=False, indent=2)


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
        'raw': payload,
    }
    
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
    """Get recent TradingView alerts."""
    alerts = _load_alerts()
    return alerts[-limit:]


def get_alerts_for_ticker(ticker: str, limit: int = 20) -> List[Dict]:
    """Get alerts for a specific ticker."""
    alerts = _load_alerts()
    filtered = [a for a in alerts if a.get('ticker', '').upper() == ticker.upper()]
    return filtered[-limit:]
