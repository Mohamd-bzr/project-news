"""iran_market.py — domestic Iranian market quotes for the channel board.

Free, key-less TGJU public feed (call1.tgju.org/ajax.json) — the same numbers
the «کارت‌های نوسان قیمت» pages run on: dollar, 18k gold, Emami coin. The
channel tab's *جیب مخاطب* factor and its price strip read from here; global
quotes stay with market_data (Yahoo/CoinGecko).

* **Toman, not rial.** TGJU publishes rial; everything Iranian on the page is
  spoken in toman — divide by ten, and keep the ounce in dollars.
* **5-minute TTL**, last-good-wins: if the feed dies the board keeps the last
  snapshot and marks it stale instead of going blank.
* Pure stdlib + requests; degrades to {"ok": False} — never raises.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import requests

TGJU_URL = "https://call1.tgju.org/ajax.json"
TTL_SECONDS = 300.0
_TIMEOUT = 10

# tgju symbol -> (our key, Persian label, unit)
_SYMBOLS: Dict[str, Dict[str, Any]] = {
    "price_dollar_rl": {"key": "dollar",     "label": "دلار",        "unit": "toman"},
    "geram18":         {"key": "gold18",     "label": "طلای ۱۸ عیار", "unit": "toman"},
    "sekee":           {"key": "coin_emami", "label": "سکه امامی",    "unit": "toman"},
    "ons":             {"key": "gold_ounce", "label": "اونس جهانی",   "unit": "dollar"},
    "tether":          {"key": "tether",     "label": "تتر",          "unit": "toman"},
}

_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def _num(s: Any) -> Optional[float]:
    """'2,695,000' -> 2695000.0 ; TGJU prints with thousands commas."""
    if s is None:
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", str(s)))
    except (TypeError, ValueError):
        return None


def snapshot(force: bool = False) -> Dict[str, Any]:
    """{ok, items: [{key,label,price,change_pct,unit,stale}], ts} — cached."""
    now = time.time()
    if not force and _CACHE["data"] and now - _CACHE["ts"] < TTL_SECONDS:
        return _CACHE["data"]
    try:
        r = requests.get(TGJU_URL, timeout=_TIMEOUT,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        cur = (r.json() or {}).get("current") or {}
        items = []
        for sym, meta in _SYMBOLS.items():
            row = cur.get(sym) or {}
            price = _num(row.get("p"))
            if price is None:
                continue
            if meta["unit"] == "toman":
                price = price / 10.0          # rial -> toman
            items.append({
                "key": meta["key"],
                "label": meta["label"],
                "price": price,
                "change_pct": _num(row.get("dp")),
                "unit": meta["unit"],
                "stale": False,
            })
        if not items:
            raise ValueError("tgju feed answered with no known symbol")
        data = {"ok": True, "items": items, "ts": now, "source": "tgju"}
        _CACHE["ts"], _CACHE["data"] = now, data
        return data
    except Exception:
        prev = _CACHE.get("data")
        if prev:
            stale = dict(prev)
            stale["items"] = [{**it, "stale": True} for it in prev.get("items", [])]
            stale["stale"] = True
            return stale
        return {"ok": False, "items": [], "ts": now, "source": "tgju"}


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(force=True), ensure_ascii=False, indent=2))
