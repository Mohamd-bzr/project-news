"""tv_ta.py — TradingView technical vote (unofficial scanner API, key-less).

The report's technical section computes everything locally from Yahoo candles;
this module adds the *independent* cross-check: TradingView's own BUY/SELL/NEUTRAL
aggregation over 26 standard indicators, the vote a desk's second screen shows.

* **Unofficial by nature** — it reads TradingView's public scanner endpoint.
  Every failure degrades to `None` and the report simply omits the vote line
  (the project's "data gap" rule: nothing is invented, nothing stalls).
* **Paced + cached**: 15-minute positive cache, 5-minute negative cache, and a
  minimum spacing between live calls so 14 reports in one cycle cannot hammer
  the scanner.
* Symbol map verified live: crypto pairs on BINANCE/crypto, metals + macro
  CFDs on their TV exchanges. Some CFD screeners are unreachable from some
  networks — those symbols just never carry a vote.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, Any]] = {}          # sym -> {"ts", "data"|None}
_LAST_LIVE = [0.0]
_MIN_GAP = 1.5            # seconds between live scanner calls
_TTL_OK = 900.0
_TTL_FAIL = 300.0

# sym -> (tv symbol, exchange, screener) — verified against the live scanner
_TVF: Dict[str, tuple] = {
    "BTC":  ("BTCUSDT",  "BINANCE",  "crypto"),
    "ETH":  ("ETHUSDT",  "BINANCE",  "crypto"),
    "SOL":  ("SOLUSDT",  "BINANCE",  "crypto"),
    "XRP":  ("XRPUSDT",  "BINANCE",  "crypto"),
    "ADA":  ("ADAUSDT",  "BINANCE",  "crypto"),
    "BNB":  ("BNBUSDT",  "BINANCE",  "crypto"),
    "DOGE": ("DOGEUSDT", "BINANCE",  "crypto"),
    "LINK": ("LINKUSDT", "BINANCE",  "crypto"),
    "XAU":  ("XAUUSD",   "OANDA",    "cfd"),
    "XAG":  ("XAGUSD",   "OANDA",    "cfd"),
    "WTI":  ("USOIL",    "TVC",      "cfd"),
    "DXY":  ("DXY",      "TVC",      "cfd"),
    "SPX":  ("SPX500",   "FOREXCOM", "cfd"),
    "VIX":  ("VIX",      "TVC",      "cfd"),
}

# Persian renderings, for any fa-facing surface that wants them
FA_REC = {"STRONG_BUY": "خرید قوی", "BUY": "خرید", "NEUTRAL": "خنثی",
          "SELL": "فروش", "STRONG_SELL": "فروش قوی"}


def technical_vote(sym: str, interval: str = "1d") -> Optional[Dict[str, Any]]:
    """{rec, buy, neutral, sell, osc, ma, interval, ts} for one asset, or None.

    None means "no vote available right now" — scanner unreachable, symbol
    unmapped, or a recent failure still inside the negative-cache window.
    """
    sym = (sym or "").upper()
    conf = _TVF.get(sym)
    if not conf:
        return None
    now = time.time()
    with _LOCK:
        entry = _CACHE.get(sym)
        if entry:
            ttl = _TTL_OK if entry.get("data") else _TTL_FAIL
            if now - entry["ts"] < ttl:
                return entry.get("data")

    data = _fetch(sym, conf, interval)
    with _LOCK:
        _CACHE[sym] = {"ts": now, "data": data}
    return data


def _fetch(sym: str, conf: tuple, interval: str) -> Optional[Dict[str, Any]]:
    # pacing: the scanner rate-limits bursts, and a 14-asset report build
    # fires right after a cycle — keep at least _MIN_GAP between live calls
    with _LOCK:
        wait = _MIN_GAP - (time.time() - _LAST_LIVE[0])
    if wait > 0:
        time.sleep(wait)
    try:
        from tradingview_ta import TA_Handler
        a = TA_Handler(symbol=conf[0], exchange=conf[1], screener=conf[2],
                       interval=interval).get_analysis()
        with _LOCK:
            _LAST_LIVE[0] = time.time()
        s = a.summary or {}
        if not s.get("RECOMMENDATION"):
            return None
        return {
            "sym": sym,
            "rec": s.get("RECOMMENDATION"),
            "buy": int(s.get("BUY") or 0),
            "neutral": int(s.get("NEUTRAL") or 0),
            "sell": int(s.get("SELL") or 0),
            "osc": (a.oscillators or {}).get("RECOMMENDATION"),
            "ma": (a.moving_averages or {}).get("RECOMMENDATION"),
            "interval": interval,
            "ts": int(time.time()),
        }
    except Exception:
        with _LOCK:
            _LAST_LIVE[0] = time.time()
        return None


if __name__ == "__main__":
    import json
    for s in ("BTC", "XAU", "DXY"):
        print(s, "->", json.dumps(technical_vote(s), ensure_ascii=False))
