#!/usr/bin/env python3
"""
MOHMD NEWS — Technical indicators
=========================================
Pure-python implementations (EMA, RSI-14 Wilder, MACD 12/26/9, ATR-14
Wilder, Bollinger 20/2, pivot levels). No pandas/numpy needed.
All functions are defensive: they return None/[] instead of raising when
there is not enough data — the report layer omits those sections.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


def stochastic(highs, lows, closes, k_period: int = 14, d_period: int = 3) -> dict:
    """Stochastic Oscillator (%K, %D)."""
    if not (highs and lows and closes) or len(closes) < k_period:
        return {"k": [], "d": []}
    n = min(len(highs), len(lows), len(closes))
    highs, lows, closes = highs[:n], lows[:n], closes[:n]
    k_vals = []
    for i in range(k_period - 1, n):
        h = max(highs[i - k_period + 1 : i + 1])
        l = min(lows[i - k_period + 1 : i + 1])
        c = closes[i]
        k = 50.0 if h == l else ((c - l) / (h - l)) * 100.0
        k_vals.append(round(k, 2))
    d_vals = []
    for i in range(d_period - 1, len(k_vals)):
        d = sum(k_vals[i - d_period + 1 : i + 1]) / d_period
        d_vals.append(round(d, 2))
    return {"k": k_vals, "d": d_vals}


def resolve_yahoo_symbol(symbol: str) -> str:
    """Map dashboard/asset symbol to Yahoo Finance ticker."""
    s = (symbol or "").strip()
    s_upper = s.upper()
    yahoo_map = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "XRP": "XRP-USD",
        "ADA": "ADA-USD",
        "BNB": "BNB-USD",
        "DOGE": "DOGE-USD",
        "XAU": "GC=F",
        "XAG": "SI=F",
        "WTI": "CL=F",
        "DXY": "DX-Y.NYB",
        "SPX": "^GSPC",
        "VIX": "^VIX",
    }
    if s_upper in yahoo_map:
        return yahoo_map[s_upper]
    try:
        from sources import ASSETS

        if s_upper in ASSETS and ASSETS[s_upper].get("yahoo"):
            return ASSETS[s_upper]["yahoo"]
    except Exception:
        pass
    return s


def yahoo_candidates(symbol: str) -> list:
    """Generate Yahoo candidate tickers for resilient querying."""
    s = (symbol or "").strip().upper().replace("/", "-").replace(" ", "")
    if not s:
        return []
    out = [s]
    if s.endswith("-USDT"):
        out.append(s[:-5] + "-USD")
    elif s.endswith("USDT") and "-" not in s:
        out.append(s[:-4] + "-USD")
    if s.endswith("-PERP"):
        out.append(s[:-5])
    if s.endswith("-USD") is False and "-" not in s and s.isalpha() and len(s) <= 5:
        out.append(s + "-USD")
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def yahoo_candles(symbol: str, tf: str = "1D", limit: int = 100) -> list:
    """Fetch OHLCV candle data from Yahoo Finance.
    Returns list of dicts: [{'time': int, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': float}, ...]
    """
    yh_sym = resolve_yahoo_symbol(symbol)
    tf_lower = str(tf).lower()

    if tf_lower in ("1h", "60", "60m"):
        interval, rng, agg = "60m", "1mo", 1
    elif tf_lower in ("4h", "240"):
        interval, rng, agg = "60m", "3mo", 4
    elif tf_lower in ("1w", "1wk", "w"):
        interval, rng, agg = "1wk", "2y", 1
    elif tf_lower in ("5m", "5"):
        interval, rng, agg = "5m", "5d", 1
    else:  # '1d', '1D', or default
        interval, rng, agg = "1d", "1y", 1

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )
    }

    candidates = yahoo_candidates(yh_sym)
    pts = []
    for cand in candidates:
        for host in ("query1", "query2"):
            try:
                url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{cand}"
                r = requests.get(
                    url,
                    params={"range": rng, "interval": interval, "includePrePost": "false"},
                    headers=headers,
                    timeout=10,
                )
                if r.status_code != 200:
                    continue
                res = ((r.json().get("chart") or {}).get("result") or [None])[0]
                if not res:
                    continue
                stamps = res.get("timestamp") or []
                q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
                opens = q.get("open") or []
                highs = q.get("high") or []
                lows = q.get("low") or []
                closes = q.get("close") or []
                vols = q.get("volume") or []

                for t, o, h, l, c, v in zip(stamps, opens, highs, lows, closes, vols):
                    if t and c is not None and o is not None and h is not None and l is not None:
                        pts.append({
                            "time": int(t),
                            "open": round(float(o), 4),
                            "high": round(float(h), 4),
                            "low": round(float(l), 4),
                            "close": round(float(c), 4),
                            "volume": round(float(v or 0), 2),
                        })
                if pts:
                    break
            except Exception:
                continue
        if pts:
            break

    # Aggregation if needed (e.g. 4H)
    if agg > 1 and pts:
        aggregated = []
        cur = None
        sec = agg * 3600
        for p in pts:
            b = p["time"] // sec
            if cur is None or b != cur["_b"]:
                if cur:
                    del cur["_b"]
                    aggregated.append(cur)
                cur = {
                    "_b": b,
                    "time": p["time"],
                    "open": p["open"],
                    "high": p["high"],
                    "low": p["low"],
                    "close": p["close"],
                    "volume": p["volume"],
                }
            else:
                cur["high"] = max(cur["high"], p["high"])
                cur["low"] = min(cur["low"], p["low"])
                cur["close"] = p["close"]
                cur["volume"] += p["volume"]
        if cur:
            del cur["_b"]
            aggregated.append(cur)
        pts = aggregated

    # Fallback to local .market_cache.json if network fetch failed
    if not pts:
        try:
            cache_file = Path(__file__).parent / ".market_cache.json"
            if cache_file.exists():
                cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
                clean_sym = symbol.upper().replace("-USD", "").replace("=F", "").replace("^", "")
                for k, v in cache_data.items():
                    if k.upper() in (symbol.upper(), clean_sym) and isinstance(v, dict) and "hist" in v:
                        hist = v["hist"]
                        c_list = hist.get("closes") or []
                        h_list = hist.get("highs") or []
                        l_list = hist.get("lows") or []
                        v_list = hist.get("volumes") or []
                        d_list = hist.get("timestamps") or []
                        fb_pts = []
                        for i in range(len(c_list)):
                            t_val = int(time.time() - (len(c_list) - i) * 86400)
                            if i < len(d_list) and d_list[i]:
                                try:
                                    t_val = int(datetime.strptime(d_list[i], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                                except Exception:
                                    pass
                            fb_pts.append({
                                "time": t_val,
                                "open": float(c_list[i]),
                                "high": float(h_list[i]) if i < len(h_list) else float(c_list[i]),
                                "low": float(l_list[i]) if i < len(l_list) else float(c_list[i]),
                                "close": float(c_list[i]),
                                "volume": float(v_list[i]) if i < len(v_list) else 0.0,
                            })
                        if fb_pts:
                            pts = fb_pts
                            break
        except Exception:
            pass

    if limit and limit > 0:
        return pts[-limit:]
    return pts




def sma(values, period: int) -> Optional[float]:
    if not values or len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values, period: int):
    if not values or len(values) < period:
        return []
    k = 2.0 / (period + 1)
    e = [sum(values[:period]) / period]  # seed with SMA
    for p in values[period:]:
        e.append(p * k + e[-1] * (1 - k))
    return e


def ema(values, period: int) -> Optional[float]:
    e = ema_series(values, period)
    return e[-1] if e else None


def rsi_wilder(closes, period: int = 14) -> Optional[float]:
    if not closes or len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram) latest values."""
    if not closes or len(closes) < slow + signal:
        return None, None, None
    ef = ema_series(closes, fast)
    es = ema_series(closes, slow)
    if not ef or not es:
        return None, None, None
    # Align lengths (EMA series start after their seed periods)
    offset = len(ef) - len(es)
    macd_line = [ef[i + offset] - es[i] for i in range(len(es))]
    sig = ema_series(macd_line, signal)
    if not sig:
        return (macd_line[-1], None, None)
    hist = macd_line[-1] - sig[-1]
    return (macd_line[-1], sig[-1], hist)


def atr14(highs, lows, closes, period: int = 14) -> Optional[float]:
    if not (highs and lows and closes) or len(closes) < period + 1:
        return None
    n = min(len(highs), len(lows), len(closes))
    highs, lows, closes = highs[:n], lows[:n], closes[:n]
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def bollinger(closes, period: int = 20, k: float = 2.0):
    m = sma(closes, period)
    if m is None:
        return None, None, None
    window = closes[-period:]
    var = sum((x - m) ** 2 for x in window) / period
    sd = var ** 0.5
    return (m + k * sd), m, (m - k * sd)


def pct(values, n: int) -> Optional[float]:
    """% change over last n points."""
    if not values or len(values) <= n:
        return None
    a, b = values[-1], values[-1 - n]
    if b == 0:
        return None
    return (a - b) / b * 100.0


def trend_term(x: Optional[float], thresholds=((0, "flat"),)) -> str:
    """Map a signed number to a word using ordered thresholds."""
    for t, w in thresholds:
        if x is not None and x >= t:
            return w
    return thresholds[-1][1] if thresholds else "flat"


def pivot_levels(closes, lookback: int = 60):
    """Nearest support below spot / resistance above spot from swing extremes."""
    if not closes or len(closes) < 10:
        return None, None
    spot = closes[-1]
    window = closes[-lookback:]
    support = max([p for p in window if p < spot], default=None)
    resistance = min([p for p in window if p > spot], default=None)
    return support, resistance


# ---------------------------------------------------------------------------
# ALIGNED SERIES — for the chart panel beside the report
# ---------------------------------------------------------------------------

def _pad(seq, period, total):
    """Left-pad a series that starts after `period` points with Nones."""
    pad = total - len(seq)
    return [None] * max(0, pad) + list(seq)


def ema_aligned(closes, period: int):
    e = ema_series(closes, period)
    if not e:
        return [None] * len(closes)
    return _pad(e, period, len(closes))


def rsi_series(closes, period: int = 14):
    """Wilder RSI as a list aligned with closes (None during warm-up)."""
    n = len(closes)
    out = [None] * n
    if n < period + 1:
        return out
    deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        rs = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + (ag / al if al else 0))
        out[i + 1] = rs
    return out


def macd_series(closes, fast=12, slow=26, signal=9):
    """Aligned MACD line / signal / histogram lists (None during warm-up)."""
    n = len(closes)
    if n < slow + signal:
        return [None] * n, [None] * n, [None] * n
    ef = ema_aligned(closes, fast)
    es = ema_aligned(closes, slow)
    line = [None if (a is None or b is None) else a - b for a, b in zip(ef, es)]
    valid = [v for v in line if v is not None]
    sig_valid = ema_series(valid, signal)
    sig = _pad(sig_valid, signal, len(valid)) if sig_valid else [None] * len(valid)
    sig = [None] * (n - len(sig)) + sig
    hist = [None if (m is None or s is None) else m - s for m, s in zip(line, sig)]
    return line, sig, hist


def bollinger_series(closes, period: int = 20, k: float = 2.0):
    up, mid, low = [], [], []
    for i in range(len(closes)):
        window = closes[max(0, i - period + 1): i + 1]
        if len(window) < period:
            up.append(None); mid.append(None); low.append(None)
            continue
        m = sum(window) / period
        sd = (sum((x - m) ** 2 for x in window) / period) ** 0.5
        up.append(m + k * sd); mid.append(m); low.append(m - k * sd)
    return up, mid, low


def chart_payload(*args, **kwargs) -> dict:
    """Build chart payload with candles + indicators.

    Supports two calling styles:
    1. chart_payload(symbol, tf='1D', limit=200) -> for interactive chart API
    2. chart_payload(md: dict, sym: str, meta: dict = None, points: int = 180) -> legacy report generator
    """
    if len(args) >= 1 and isinstance(args[0], dict):
        md = args[0]
        sym = args[1] if len(args) > 1 else kwargs.get("sym", "")
        meta = args[2] if len(args) > 2 else kwargs.get("meta") or {}
        points = args[3] if len(args) > 3 else kwargs.get("points", 180)

        closes = list(md.get("closes") or [])
        highs = list(md.get("highs") or [])
        lows = list(md.get("lows") or [])
        vols = list(md.get("volumes") or [])
        ts = list(md.get("timestamps") or [])
        if not closes:
            return {"sym": sym, "empty": True, "candles": []}

        n = len(closes)
        e20 = ema_aligned(closes, 20)
        e50 = ema_aligned(closes, 50)
        e200 = ema_aligned(closes, 200)
        rsi = rsi_series(closes, 14)
        mline, msig, mhist = macd_series(closes)
        bu, bm, bl = bollinger_series(closes, 20, 2.0)

        def tail(seq):
            seq = list(seq) if seq else []
            return seq[-points:] if len(seq) >= points else [None] * (points - len(seq)) + seq

        sup, res = pivot_levels(closes, min(60, n))

        tail_closes = closes[-points:]
        tail_highs = highs[-points:] if highs else []
        tail_lows = lows[-points:] if lows else []
        tail_vols = vols[-points:] if vols else []
        tail_ts = ts[-points:] if ts else []

        candles = []
        for i in range(len(tail_closes)):
            c = tail_closes[i]
            t = tail_ts[i] if i < len(tail_ts) else i
            if isinstance(t, str) and "-" in t:
                try:
                    t = int(datetime.strptime(t, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                except Exception:
                    pass
            candles.append({
                "time": t,
                "open": float(c) if c is not None else 0.0,
                "high": float(tail_highs[i]) if i < len(tail_highs) and tail_highs[i] is not None else float(c or 0),
                "low": float(tail_lows[i]) if i < len(tail_lows) and tail_lows[i] is not None else float(c or 0),
                "close": float(c) if c is not None else 0.0,
                "volume": float(tail_vols[i]) if i < len(tail_vols) and tail_vols[i] is not None else 0.0,
            })

        return {
            "sym": sym,
            "name": meta.get("name", sym),
            "fa": meta.get("fa", sym),
            "icon": meta.get("icon", ""),
            "price": md.get("price"),
            "change_24h": md.get("change_24h"),
            "stale": bool(md.get("stale")),
            "dates": tail_ts,
            "closes": tail_closes,
            "candles": candles,
            "ema20": tail(e20),
            "ema50": tail(e50),
            "ema200": tail(e200),
            "bb_up": tail(bu),
            "bb_low": tail(bl),
            "bb_mid": tail(bm),
            "rsi": tail(rsi),
            "macd": tail(mline),
            "macd_signal": tail(msig),
            "macd_hist": tail(mhist),
            "volumes": tail_vols,
            "highs": tail_highs,
            "lows": tail_lows,
            "support": sup,
            "resistance": res,
            "atr14": atr14(highs, lows, closes) if (highs and lows) else None,
            "n": n,
        }
    else:
        symbol = args[0] if len(args) > 0 else kwargs.get("symbol", "BTC")
        tf = args[1] if len(args) > 1 else kwargs.get("tf", "1D")
        limit = args[2] if len(args) > 2 else kwargs.get("limit", 200)

        candles = yahoo_candles(symbol, tf=tf, limit=limit)
        if not candles:
            return {}

        dates = [c["time"] for c in candles]
        opens = [c["open"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]

        ema20_list = [round(x, 4) for x in ema_series(closes, 20)]
        ema50_list = [round(x, 4) for x in ema_series(closes, 50)]
        rsi_full = rsi_series(closes, 14)
        rsi_list = [round(x, 2) for x in rsi_full if x is not None]
        mline, msig, mhist = macd_series(closes)
        macd_dict = {
            "macd": [round(x, 4) for x in mline if x is not None],
            "signal": [round(x, 4) for x in msig if x is not None],
            "hist": [round(x, 4) for x in mhist if x is not None],
        }
        stoch_dict = stochastic(highs, lows, closes)

        return {
            "candles": candles,
            "ema20": ema20_list,
            "ema50": ema50_list,
            "rsi": rsi_list,
            "macd": macd_dict,
            "stoch": stoch_dict,
            "dates": dates,
            "symbol": symbol,
            "closes": closes,
            "highs": highs,
            "lows": lows,
            "volumes": volumes,
        }





def snapshot(closes, volumes=None, highs=None, lows=None) -> dict:
    """
    Build the full indicator snapshot used by the report generator.
    Returns a flat dict of metrics (any metric may be None).
    """
    closes = list(closes) if closes else []
    snap = {}
    spot = closes[-1] if closes else None
    snap["spot"] = spot
    snap["n"] = len(closes)

    snap["ema20"] = ema(closes, 20)
    snap["ema50"] = ema(closes, 50)
    snap["ema200"] = ema(closes, 200)
    snap["rsi14"] = rsi_wilder(closes, 14)
    m, s, h = macd(closes)
    snap["macd"] = m
    snap["macd_signal"] = s
    snap["macd_hist"] = h
    up, mid, low = bollinger(closes, 20, 2.0)
    snap["bb_up"] = up
    snap["bb_mid"] = mid
    snap["bb_low"] = low
    if highs and lows and closes:
        snap["atr14"] = atr14(highs, lows, closes)
    else:
        snap["atr14"] = None
    if closes:
        sup, res = pivot_levels(closes, 60)
        snap["support"] = sup
        snap["resistance"] = res
    else:
        snap["support"] = snap["resistance"] = None
    snap["chg7d"] = pct(closes, 7)
    snap["chg30d"] = pct(closes, 30)
    snap["chg90d"] = pct(closes, 90)

    if volumes and len(volumes) == len(closes):
        cur = sum(volumes[-7:]) / 7.0
        base = sum(volumes[-30:-7]) / max(1, len(volumes[-30:-7])) if len(volumes) >= 30 else None
        snap["vol_ratio_7d_vs_30d"] = (cur / base) if (base and cur) else None
    else:
        snap["vol_ratio_7d_vs_30d"] = None

    return snap
